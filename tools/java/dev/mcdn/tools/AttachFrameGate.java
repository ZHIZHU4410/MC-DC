package dev.mcdn.tools;
import com.sun.tools.attach.VirtualMachine;

public final class AttachFrameGate {
    public static void main(String[] args) {
        try {
            VirtualMachine target=VirtualMachine.attach(args[0]);
            try{target.loadAgent(args[1],args[2]);}finally{target.detach();}
            System.out.println("FRAME_GATE_DIAG_ATTACH_RETURNED");
        }catch(Throwable error){System.err.println("FRAME_GATE_DIAG_ATTACH_FAILED "+error);System.exit(2);}
    }
}
