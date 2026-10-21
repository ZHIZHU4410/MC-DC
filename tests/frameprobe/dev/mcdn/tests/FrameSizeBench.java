package dev.mcdn.tests;
import dev.mcdn.frameprobe.FrameSize;

/** Regression for the actual 2560x1494 window failure; also portrait, no upscaling, thin and bounded input. */
public final class FrameSizeBench {
    public static void main(String[] args) {
        int[][] cases={{2560,1494,1024,598},{1494,2560,598,1024},{1920,1080,1024,576},{739,497,739,497},{3840,2160,1024,576},{3840,1,1024,1},{1,2160,1,1024}};
        for(int[] c:cases){var got=FrameSize.fit(c[0],c[1]);if(got.width()!=c[2]||got.height()!=c[3])throw new AssertionError("native window size regression");}
        for(int[] c:new int[][]{{0,1},{1,0},{-1,1},{Integer.MAX_VALUE,Integer.MAX_VALUE},{3841,2160}}){boolean rejected=false;try{FrameSize.fit(c[0],c[1]);}catch(IllegalArgumentException ex){rejected=true;}if(!rejected)throw new AssertionError("unbounded readback");}
        System.out.println("FRAME_SIZE_PASS actual 2560x1494 regression and 11 size boundaries");
    }
}
