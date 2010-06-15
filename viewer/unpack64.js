/*
 * unpack64: decodes a pack64'd string into a vector.
 *
 * This function is for decoding a packed vector format, defined in the
 * Python csc-utils package as csc.util.vector.pack64. The format uses URL-safe
 * base64 to encode an exponent followed by several 18-bit signed integers.
 */

base64_alphabet =
"ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
base64_map = {};
for (var i=0; i<64; i++) {
    base64_map[base64_alphabet.charAt(i)] = i;
}

/* 2^17 is the number that makes an 18-bit signed integer go negative. */
SIGN_BIT = 131072;

function unpack64(str) {
    var hexes = [];
    for (var i=0; i<str.length; i++) {
        hexes[i] = base64_map[str.charAt(i)];
    }
    var vector = [];
    var K = (hexes.length-1)/3;
    var unit = Math.pow(2, hexes[0] - 40);
    for (var i=0; i<K; i++) {
        var integer = hexes[i*3 + 1]*4096 + hexes[i*3+2]*64 + hexes[i*3+3];
        if (integer >= SIGN_BIT) integer -= SIGN_BIT*2;
        vector[i] = integer * unit;
    }
    return vector;
}
