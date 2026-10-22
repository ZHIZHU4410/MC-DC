package dev.mcdn.physics;

import com.google.gson.JsonObject;
import dev.mcdn.protocol.Control;
import dev.mcdn.protocol.Wire;
import dev.mcdn.protocol.World;
import java.net.InetAddress;
import java.net.ServerSocket;
import java.nio.file.Files;
import java.nio.file.Path;
import java.security.MessageDigest;
import java.time.Duration;
import java.util.HexFormat;
import java.util.UUID;

/** Real socket handshake after the former 30-second MC-first startup limit. */
public final class WarmStartBench {
    private WarmStartBench() {}

    public static void main(String[] args) throws Exception {
        Path jar = Path.of(args[0]), scene = Path.of(args[1]), directory = Path.of(args[2]);
        Files.createDirectories(directory);
        World world = World.decode(Files.readAllBytes(scene));
        UUID session = UUID.randomUUID();
        String nonce = "a".repeat(64), dcBuild = "b".repeat(64);
        var config = new JsonObject();
        config.addProperty("inputLab", true);
        config.addProperty("eligibleForControl", false);
        config.addProperty("geometryDigest", world.stamp().digest());
        config.addProperty("session", session.toString());
        config.addProperty("controlNonce", nonce);
        config.addProperty("mcBuild", hex(Files.readAllBytes(jar)));
        config.addProperty("dcBuild", dcBuild);
        config.addProperty("controlPort", 0);
        config.addProperty("expiresUnixMs", System.currentTimeMillis() + Duration.ofSeconds(90).toMillis());
        Path manifest = directory.resolve("warm-start-manifest.json");
        Files.writeString(manifest, config.toString());
        LabControlGuest guest = new LabControlGuest(manifest, hex(Files.readAllBytes(manifest)), world);
        Thread.sleep(Duration.ofSeconds(32));
        if (guest.failure() != null || guest.inbox() != null)
            throw new IllegalStateException("MC standby failed before DC was ready: " + guest.failure());
        try (var listener = new ServerSocket(0, 1, InetAddress.getLoopbackAddress())) {
            listener.setSoTimeout(5000);
            var endpoint = new JsonObject();
            endpoint.addProperty("session", session.toString());
            endpoint.addProperty("dcBuild", dcBuild);
            endpoint.addProperty("port", listener.getLocalPort());
            Files.writeString(directory.resolve("control-endpoint.json"), endpoint.toString());
            try (var socket = listener.accept()) {
                socket.setSoTimeout(5000);
                byte[] buffer = new byte[4096];
                int length = socket.getInputStream().read(buffer);
                if (length <= 0) throw new IllegalStateException("MC HELLO absent");
                var decoder = new Wire.StreamDecoder();
                final int[] hellos = {0};
                decoder.feed(buffer, 0, length, message -> {
                    new Control.Handshake().accept(message, session, 1, "mc", nonce, config.get("mcBuild").getAsString());
                    hellos[0]++;
                });
                if (hellos[0] != 1) throw new IllegalStateException("MC HELLO incomplete");
                socket.getOutputStream().write(Wire.encode(new Wire.Envelope(2, session, 0, 0, 1, 1,
                    Control.hello("dc", nonce, dcBuild, ProcessHandle.current().pid(), 1))));
                long deadline = System.nanoTime() + Duration.ofSeconds(3).toNanos();
                while (guest.inbox() == null && guest.failure() == null && System.nanoTime() < deadline)
                    Thread.sleep(10);
                if (guest.inbox() == null || guest.failure() != null)
                    throw new IllegalStateException("late DC handshake failed: " + guest.failure());
                System.out.println("MC_FIRST_STANDBY_PASS delayedSeconds=32 hello=1 lateHandshake=true");
            }
        }
    }

    private static String hex(byte[] data) throws Exception {
        return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(data));
    }
}
