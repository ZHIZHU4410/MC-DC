package dev.mcdn.frameprobe;

/** CPU diagnostic output size, independent of the source dimensions' common divisors. */
public record FrameSize(int width,int height) {
    public static FrameSize fit(int sourceWidth,int sourceHeight) {
        if(sourceWidth<1||sourceHeight<1||(long)sourceWidth*sourceHeight>3840L*2160)throw new IllegalArgumentException("bounded source size");
        double scale=Math.min(1.0,1024.0/Math.max(sourceWidth,sourceHeight));
        return new FrameSize(Math.max(1,(int)Math.round(sourceWidth*scale)),Math.max(1,(int)Math.round(sourceHeight*scale)));
    }
}
