#include <windows.h>
#include <sddl.h>
#include <cstdint>
#include <cstring>
#include <cstdio>
#include <memory>
#include <string>
#include <vector>
#include "dev_mcdn_ipc_NativeMailbox.h"

// The mapped-file algorithm is shared by JNI and P/Invoke. No managed cross-process atomics.
static_assert(sizeof(void*)==8 && sizeof(wchar_t)==2);
namespace {
constexpr uint32_t Header=64, FrameHeader=256, MaxSlot=384+1024*1024*4;
uint32_t u32(const uint8_t* p){uint32_t v;std::memcpy(&v,p,4);return v;}
uint64_t u64(const uint8_t* p){uint64_t v;std::memcpy(&v,p,8);return v;}
void p32(uint8_t* p,uint32_t v){std::memcpy(p,&v,4);}
void p64(uint8_t* p,uint64_t v){std::memcpy(p,&v,8);}
struct Security {
    PSECURITY_DESCRIPTOR descriptor=nullptr;
    SECURITY_ATTRIBUTES attrs{sizeof(SECURITY_ATTRIBUTES),nullptr,FALSE};
    explicit Security(bool inherit=false){
        HANDLE token=nullptr;
        if(!OpenProcessToken(GetCurrentProcess(),TOKEN_QUERY,&token))throw GetLastError();
        DWORD bytes=0;GetTokenInformation(token,TokenUser,nullptr,0,&bytes);
        std::vector<uint8_t> data(bytes);
        if(!GetTokenInformation(token,TokenUser,data.data(),bytes,&bytes)){DWORD e=GetLastError();CloseHandle(token);throw e;}
        CloseHandle(token);LPWSTR sid=nullptr;
        if(!ConvertSidToStringSidW(reinterpret_cast<TOKEN_USER*>(data.data())->User.Sid,&sid))throw GetLastError();
        std::wstring ace=inherit?L";OICI;GA;;;":L";;GA;;;";
        std::wstring sddl=L"D:P(A"+ace+sid+L")(A"+ace+L"SY)";LocalFree(sid);
        if(!ConvertStringSecurityDescriptorToSecurityDescriptorW(sddl.c_str(),SDDL_REVISION_1,&descriptor,nullptr))throw GetLastError();
        attrs.lpSecurityDescriptor=descriptor;
    }
    ~Security(){DWORD e=GetLastError();if(descriptor)LocalFree(descriptor);SetLastError(e);}
};
struct Mailbox {
    HANDLE file=INVALID_HANDLE_VALUE,map=nullptr,locks[4]{};
    uint8_t* data=nullptr;
    uint8_t session[16]{};
    uint32_t slotBytes=0,next=0;
    bool worldColor=false;
    uint32_t frameHeader()const{return worldColor?384:256;}
    const char* frameMagic()const{return worldColor?"MCWC\0\0\1\0":"MCDF\0\0\1\0";}
    const char* boxMagic()const{return worldColor?"MCDM\0\0\2\0":"MCDM\0\0\1\0";}
    uint64_t consumed=0;
    DWORD owner=GetCurrentThreadId();
    bool debugHeld[4]{};
    ~Mailbox(){DWORD e=GetLastError();if(data)UnmapViewOfFile(data);if(map)CloseHandle(map);if(file!=INVALID_HANDLE_VALUE)CloseHandle(file);for(auto h:locks)if(h)CloseHandle(h);SetLastError(e);}
    LONG fault()const{return InterlockedCompareExchange(reinterpret_cast<volatile LONG*>(data+48),0,0);}
    int poison(){InterlockedExchange(reinterpret_cast<volatile LONG*>(data+48),1);return -2;}
    bool validThread()const{return owner==GetCurrentThreadId();}
    int lock(int which){
        if(!validThread()||which<0||which>3)return -1;
        if(fault()!=0)return -2;
        DWORD result=WaitForSingleObject(locks[which],0);
        if(result==WAIT_OBJECT_0)return 1;
        if(result==WAIT_TIMEOUT)return 0;
        if(result==WAIT_ABANDONED){poison();ReleaseMutex(locks[which]);return -2;}
        return poison();
    }
    bool unlock(int which){if(ReleaseMutex(locks[which]))return true;poison();return false;}
    bool header()const{
        return std::memcmp(data,boxMagic(),8)==0&&u32(data+8)==Header&&u32(data+12)==slotBytes&&
            std::memcmp(data+16,session,16)==0&&u32(data+32)==3&&u32(data+52)==(worldColor?1u:0u)&&u64(data+56)==0&&fault()==0;
    }
    uint8_t* slot(uint32_t index)const{return data+Header+static_cast<size_t>(index)*slotBytes;}
    int capture(uint32_t& index,uint64_t& id){
        int held=lock(0);if(held!=1)return held;
        bool ok=header();index=u32(data+36);id=u64(data+40);unlock(0);
        if(!ok)return poison();
        if(index==UINT32_MAX&&id==0)return 0;
        if(index>=3||id==0)return poison();
        return fault()==0?1:-2;
    }
    int copy(uint32_t index,uint64_t id,uint8_t* output,uint32_t capacity,uint32_t& size){
        size=0;if(index>=3||id==0)return -1;
        if(id<=consumed)return 0;
        int held=lock(static_cast<int>(index)+1);if(held!=1)return held;
        const uint8_t* source=slot(index);
        if(u64(source+56)!=id){unlock(static_cast<int>(index)+1);return 0;} // publication captured before slot reuse
        uint64_t length=static_cast<uint64_t>(frameHeader())+u32(source+12);
        bool ok=length<=slotBytes&&length<=capacity&&std::memcmp(source,frameMagic(),8)==0&&
            u32(source+8)==frameHeader()&&std::memcmp(source+16,session,16)==0;
        if(ok){size=static_cast<uint32_t>(length);std::memcpy(output,source,size);}
        unlock(static_cast<int>(index)+1);
        if(!ok)return poison();
        if(fault()!=0){size=0;return -2;}
        consumed=id;return 1;
    }
};
Mailbox* openBox(const wchar_t* path,const uint8_t* session,uint32_t slotBytes,bool create,bool worldColor=false){
    if(!path||!session||slotBytes<(worldColor?384u:256u)||slotBytes>(worldColor?MaxSlot:256u+1024u*1024u*4u)){SetLastError(ERROR_INVALID_PARAMETER);return nullptr;}
    try{
        auto box=std::make_unique<Mailbox>();box->worldColor=worldColor;box->slotBytes=slotBytes;std::memcpy(box->session,session,16);
        Security security;
        box->file=CreateFileW(path,GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,create?&security.attrs:nullptr,
            create?CREATE_NEW:OPEN_EXISTING,FILE_ATTRIBUTE_NORMAL,nullptr);
        if(box->file==INVALID_HANDLE_VALUE)return nullptr;
        LARGE_INTEGER length;length.QuadPart=Header+3LL*slotBytes;
        if(create){if(!SetFilePointerEx(box->file,length,nullptr,FILE_BEGIN)||!SetEndOfFile(box->file))return nullptr;}
        else{LARGE_INTEGER actual;if(!GetFileSizeEx(box->file,&actual)||actual.QuadPart!=length.QuadPart){SetLastError(ERROR_INVALID_DATA);return nullptr;}}
        box->map=CreateFileMappingW(box->file,nullptr,PAGE_READWRITE,0,static_cast<DWORD>(length.QuadPart),nullptr);
        if(!box->map)return nullptr;
        box->data=static_cast<uint8_t*>(MapViewOfFile(box->map,FILE_MAP_READ|FILE_MAP_WRITE,0,0,static_cast<SIZE_T>(length.QuadPart)));
        if(!box->data)return nullptr;
        constexpr wchar_t hex[]=L"0123456789abcdef";std::wstring prefix=L"Local\\MCDN_";
        for(int i=0;i<16;i++){prefix+=hex[session[i]>>4];prefix+=hex[session[i]&15];}
        if(worldColor)prefix+=L"_WorldColor";
        for(int i=0;i<4;i++){
            std::wstring name=prefix+(i==0?L"_Publication":L"_FrameSlot_"+std::to_wstring(i-1));
            box->locks[i]=create?CreateMutexW(&security.attrs,FALSE,name.c_str()):OpenMutexW(SYNCHRONIZE|MUTEX_MODIFY_STATE,FALSE,name.c_str());
            if(!box->locks[i])return nullptr;
            if(create&&GetLastError()==ERROR_ALREADY_EXISTS){SetLastError(ERROR_ALREADY_EXISTS);return nullptr;}
        }
        if(create){
            // This new private file has no valid fault word until its initial header is written.
            if(WaitForSingleObject(box->locks[0],0)!=WAIT_OBJECT_0){SetLastError(ERROR_BUSY);return nullptr;}
            std::memset(box->data,0,Header);std::memcpy(box->data,box->boxMagic(),8);p32(box->data+8,Header);p32(box->data+12,slotBytes);
            std::memcpy(box->data+16,session,16);p32(box->data+32,3);p32(box->data+36,UINT32_MAX);p32(box->data+52,worldColor?1u:0u);box->unlock(0);
        }else{
            int held=box->lock(0);
            if(held!=1){SetLastError(held==0?ERROR_BUSY:ERROR_INVALID_DATA);return nullptr;}
            bool ok=box->header();box->unlock(0);if(!ok){SetLastError(ERROR_INVALID_DATA);return nullptr;}
        }
        return box.release();
    }catch(DWORD e){SetLastError(e);return nullptr;}catch(...){SetLastError(ERROR_NOT_ENOUGH_MEMORY);return nullptr;}
}
void jerror(JNIEnv* env,const char* what){
    char message[160];sprintf_s(message,"%s (Win32=%lu)",what,GetLastError());
    env->ThrowNew(env->FindClass("java/lang/IllegalStateException"),message);
}
Mailbox* from(jlong value){return reinterpret_cast<Mailbox*>(static_cast<uintptr_t>(value));}
}

#define API extern "C" __declspec(dllexport)
API uint32_t mcdn_api_version(){return 1;}
API int mcdn_private_directory(const wchar_t* path){try{Security security(true);return CreateDirectoryW(path,&security.attrs)?1:0;}catch(...){return 0;}}
API void* mcdn_open(const wchar_t* path,const uint8_t* session,uint32_t slotBytes,int create){return openBox(path,session,slotBytes,create!=0);}
API void* mcdn_open_world_color(const wchar_t* path,const uint8_t* session,uint32_t slotBytes,int create){return openBox(path,session,slotBytes,create!=0,true);}
API void mcdn_close(void* handle){delete static_cast<Mailbox*>(handle);}
API void mcdn_poison(void* handle){if(handle)static_cast<Mailbox*>(handle)->poison();}
API int64_t mcdn_qpc(){LARGE_INTEGER value;return QueryPerformanceCounter(&value)?value.QuadPart:0;}
API int64_t mcdn_frequency(){LARGE_INTEGER value;return QueryPerformanceFrequency(&value)?value.QuadPart:0;}
API int mcdn_capture(void* handle,uint32_t* index,uint64_t* id){return handle&&index&&id?static_cast<Mailbox*>(handle)->capture(*index,*id):-1;}
API int mcdn_read_captured(void* handle,uint32_t index,uint64_t id,uint8_t* output,uint32_t capacity,uint32_t* size){
    return handle&&output&&size?static_cast<Mailbox*>(handle)->copy(index,id,output,capacity,*size):-1;
}
API int mcdn_read(void* handle,uint8_t* output,uint32_t capacity,uint32_t* size){
    if(!handle||!output||!size)return -1;
    auto box=static_cast<Mailbox*>(handle);*size=0;uint32_t index=0;uint64_t id=0;
    int result=box->capture(index,id);return result==1?box->copy(index,id,output,capacity,*size):result;
}
API int mcdn_publish(void* handle,const uint8_t* frame,uint32_t bytes){
    if(!handle||!frame)return -1;auto box=static_cast<Mailbox*>(handle);
    if(!box->validThread()||bytes<box->frameHeader()||bytes>box->slotBytes||std::memcmp(frame,box->frameMagic(),8)!=0||
        u32(frame+8)!=box->frameHeader()||static_cast<uint64_t>(u32(frame+12))+box->frameHeader()!=bytes||std::memcmp(frame+16,box->session,16)!=0||u64(frame+56)==0)return -1;
    uint32_t current=0;uint64_t previous=0;
    int held=box->lock(0);if(held!=1)return held;
    bool ok=box->header();current=u32(box->data+36);previous=u64(box->data+40);box->unlock(0);
    if(!ok)return box->poison();uint64_t id=u64(frame+56);if(id<=previous)return -1;
    for(uint32_t attempt=0;attempt<3;attempt++){
        uint32_t index=box->next++%3;if(index==current)continue;
        held=box->lock(static_cast<int>(index)+1);if(held<0)return held;if(held==0)continue;
        std::memcpy(box->slot(index),frame,bytes);box->unlock(static_cast<int>(index)+1);
        held=box->lock(0);if(held!=1)return held;
        if(box->fault()!=0){box->unlock(0);return -2;}
        if(u64(box->data+40)>=id){box->unlock(0);return -1;}
        p32(box->data+36,index);p64(box->data+40,id);box->unlock(0);return box->fault()==0?1:-2;
    }
    return 0;
}
// Explicit diagnostic exports; not called by game adapters.
API int mcdn_diagnostic_lock(void* handle,int which){if(!handle)return -1;auto box=static_cast<Mailbox*>(handle);int r=box->lock(which);if(r==1)box->debugHeld[which]=true;return r;}
API int mcdn_diagnostic_unlock(void* handle,int which){if(!handle||which<0||which>3)return 0;auto box=static_cast<Mailbox*>(handle);if(!box->debugHeld[which])return 0;box->debugHeld[which]=false;return box->unlock(which)?1:0;}
API int mcdn_diagnostic_partial_write(void* handle,int which){
    if(!handle||which<0||which>3)return 0;auto box=static_cast<Mailbox*>(handle);
    if(!box->validThread()||!box->debugHeld[which])return 0;
    if(which==0)p32(box->data+36,1);else if(box->slotBytes>box->frameHeader())std::memset(box->slot(static_cast<uint32_t>(which-1))+box->frameHeader(),0xa5,1);
    return 1;
}

JNIEXPORT jint JNICALL Java_dev_mcdn_ipc_NativeMailbox_api0(JNIEnv*,jclass){return 1;}
JNIEXPORT jlong JNICALL Java_dev_mcdn_ipc_NativeMailbox_open0(JNIEnv* env,jclass,jstring path,jbyteArray id,jint capacity){
    if(!path||!id||env->GetArrayLength(id)!=16||capacity<0){jerror(env,"invalid mailbox open arguments");return 0;}
    try{
        std::wstring file(static_cast<size_t>(env->GetStringLength(path)),L'\0');
        env->GetStringRegion(path,0,env->GetStringLength(path),reinterpret_cast<jchar*>(file.data()));
        if(env->ExceptionCheck())return 0;
        uint8_t session[16];env->GetByteArrayRegion(id,0,16,reinterpret_cast<jbyte*>(session));
        if(env->ExceptionCheck())return 0;
        auto result=openBox(file.c_str(),session,static_cast<uint32_t>(capacity),false);
        if(!result)jerror(env,"open native mailbox failed");return static_cast<jlong>(reinterpret_cast<uintptr_t>(result));
    }catch(...){SetLastError(ERROR_NOT_ENOUGH_MEMORY);jerror(env,"native open allocation failed");return 0;}
}
JNIEXPORT jlong JNICALL Java_dev_mcdn_ipc_NativeMailbox_openWorld0(JNIEnv* env,jclass,jstring path,jbyteArray id,jint capacity){
    if(!path||!id||env->GetArrayLength(id)!=16||capacity<0){jerror(env,"invalid mailbox open arguments");return 0;}
    try{
        std::wstring file(static_cast<size_t>(env->GetStringLength(path)),L'\0');
        env->GetStringRegion(path,0,env->GetStringLength(path),reinterpret_cast<jchar*>(file.data()));
        if(env->ExceptionCheck())return 0;
        uint8_t session[16];env->GetByteArrayRegion(id,0,16,reinterpret_cast<jbyte*>(session));
        if(env->ExceptionCheck())return 0;
        auto result=openBox(file.c_str(),session,static_cast<uint32_t>(capacity),false,true);
        if(!result)jerror(env,"open native mailbox failed");return static_cast<jlong>(reinterpret_cast<uintptr_t>(result));
    }catch(...){SetLastError(ERROR_NOT_ENOUGH_MEMORY);jerror(env,"native open allocation failed");return 0;}
}
JNIEXPORT void JNICALL Java_dev_mcdn_ipc_NativeMailbox_close0(JNIEnv*,jclass,jlong box){mcdn_close(from(box));}
JNIEXPORT void JNICALL Java_dev_mcdn_ipc_NativeMailbox_poison0(JNIEnv*,jclass,jlong box){mcdn_poison(from(box));}
JNIEXPORT jlong JNICALL Java_dev_mcdn_ipc_NativeMailbox_qpc0(JNIEnv*,jclass){return mcdn_qpc();}
JNIEXPORT jlong JNICALL Java_dev_mcdn_ipc_NativeMailbox_frequency0(JNIEnv*,jclass){return mcdn_frequency();}
JNIEXPORT jboolean JNICALL Java_dev_mcdn_ipc_NativeMailbox_publish0(JNIEnv* env,jclass,jlong value,jbyteArray packet){
    try{
        if(!packet){jerror(env,"null frame");return JNI_FALSE;}
        jsize size=env->GetArrayLength(packet);if(size<256||size>static_cast<jsize>(MaxSlot)){jerror(env,"frame size");return JNI_FALSE;}
        std::vector<uint8_t> bytes(static_cast<size_t>(size));env->GetByteArrayRegion(packet,0,size,reinterpret_cast<jbyte*>(bytes.data()));
        int result=mcdn_publish(from(value),bytes.data(),static_cast<uint32_t>(size));if(result<0)jerror(env,"native publish fault");return result==1?JNI_TRUE:JNI_FALSE;
    }catch(...){jerror(env,"native publish allocation failed");return JNI_FALSE;}
}
JNIEXPORT jbyteArray JNICALL Java_dev_mcdn_ipc_NativeMailbox_read0(JNIEnv* env,jclass,jlong value){
    try{
        auto box=from(value);if(!box){jerror(env,"closed native mailbox");return nullptr;}
        std::vector<uint8_t> bytes(box->slotBytes);uint32_t size=0;int result=mcdn_read(box,bytes.data(),box->slotBytes,&size);
        if(result<0){jerror(env,"native read fault");return nullptr;}if(result==0)return nullptr;
        auto output=env->NewByteArray(static_cast<jsize>(size));if(output)env->SetByteArrayRegion(output,0,static_cast<jsize>(size),reinterpret_cast<const jbyte*>(bytes.data()));return output;
    }catch(...){jerror(env,"native read allocation failed");return nullptr;}
}
JNIEXPORT jlongArray JNICALL Java_dev_mcdn_ipc_NativeMailbox_capture0(JNIEnv* env,jclass,jlong value){
    uint32_t index=0;uint64_t id=0;int result=mcdn_capture(from(value),&index,&id);if(result<0){jerror(env,"native capture fault");return nullptr;}if(!result)return nullptr;
    jlong values[2]{static_cast<jlong>(index),static_cast<jlong>(id)};auto output=env->NewLongArray(2);if(output)env->SetLongArrayRegion(output,0,2,values);return output;
}
JNIEXPORT jboolean JNICALL Java_dev_mcdn_ipc_NativeMailbox_lock0(JNIEnv* env,jclass,jlong value,jint which){int r=mcdn_diagnostic_lock(from(value),which);if(r<0)jerror(env,"diagnostic lock fault");return r==1?JNI_TRUE:JNI_FALSE;}
JNIEXPORT void JNICALL Java_dev_mcdn_ipc_NativeMailbox_unlock0(JNIEnv* env,jclass,jlong value,jint which){if(!mcdn_diagnostic_unlock(from(value),which))jerror(env,"diagnostic unlock fault");}
JNIEXPORT void JNICALL Java_dev_mcdn_ipc_NativeMailbox_corrupt0(JNIEnv* env,jclass,jlong value,jint which){if(!mcdn_diagnostic_partial_write(from(value),which))jerror(env,"diagnostic write without lock");}
