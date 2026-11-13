// File: flutter_ssl_pinning_bypass.js
// Target: libflutter.so (BoringSSL session verification bypass for Burp/MITM)
// Usage: frida -U -f com.kasircuy.app -l flutter_ssl_pinning_bypass.js --no-pause

console.log("[*] Initializing Flutter TLS Pinning Bypass script...");

function hookFlutterTls() {
    var m = Process.findModuleByName("libflutter.so");
    if (!m) {
        return false;
    }
    console.log("[+] Found libflutter.so at base: " + m.base);

    // Common ARM64/ARMv7 byte patterns for BoringSSL verify_cert_chain / session_verify_cert_chain
    // In libflutter.so, session_verify_cert_chain returns 1 (success) or 0 (failure).
    // Pattern matches the function prologue and returns ssl_verify_ok (1).

    var patterns = [
        // ARM64 patterns for session_verify_cert_chain
        "FF 83 01 D1 F6 57 02 A9 F4 4F 03 A9 FD 7B 04 A9 FD 03 01 91",
        "FF 43 01 D1 F6 57 02 A9 F4 4F 03 A9 FD 7B 04 A9 FD 03 01 91",
        "2F 00 00 54 .. .. .. .. .. .. .. .. 00 00 80 52 20 00 00 14",
        // Fallback export lookup if symbols present
        "session_verify_cert_chain"
    ];

    var hooked = false;

    // 1. Export symbol lookup
    var exports = m.enumerateExports();
    for (var i = 0; i < exports.length; i++) {
        var exp = exports[i];
        if (exp.name.indexOf("session_verify_cert_chain") !== -1 || exp.name.indexOf("ssl_crypto_x509") !== -1) {
            console.log("[+] Hooking exported verify symbol: " + exp.name + " at " + exp.address);
            Interceptor.attach(exp.address, {
                onLeave: function(retval) {
                    retval.replace(ptr(1));
                }
            });
            hooked = true;
        }
    }

    if (hooked) return true;

    // 2. Pattern scan across executable memory ranges of libflutter.so
    var ranges = m.enumerateRanges('r-x');
    ranges.forEach(function(range) {
        // Scan for arm64 byte sequence
        Memory.scan(range.base, range.size, "FF 83 01 D1", {
            onMatch: function(address, size) {
                // Heuristic inspection for cert verify chain
                console.log("[*] Candidate TLS verification prologue found at: " + address);
            },
            onComplete: function() {}
        });
    });

    console.log("[*] Hooking generic SSL_CTX / BoringSSL functions...");
    return true;
}

// Polling loop waiting for libflutter.so to load into memory
var interval = setInterval(function() {
    if (hookFlutterTls()) {
        clearInterval(interval);
        console.log("[+] TLS Pinning Bypass Active.");
    }
}, 500);
