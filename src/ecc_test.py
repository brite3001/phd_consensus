from py_ecc.bls import G2ProofOfPossession as bls_pop
import sys
import base64

private_key = 5566
public_key = bls_pop.SkToPk(private_key)
print(public_key)

x = base64.b64encode(public_key).decode("utf-8")
x = base64.b64decode(x)

print(x)


message = b"\xab" * 32  # The message to be signed

# Signing
signature = bls_pop.Sign(private_key, message)

# Verifying
assert bls_pop.Verify(x, message, signature)

private_keys = [5566, 5566, 5566, 5566, 5566, 5566, 5566, 5566, 5566]


messages = [
    b"\xaa" * 42,
    b"\xbb" * 32,
    b"\xcc" * 64,
    b"\xaa" * 42,
    b"\xbb" * 32,
    b"\xcc" * 64,
    b"\xaa" * 42,
    b"\xbb" * 32,
    b"\xcc" * 64,
]

signatures = [
    bls_pop.Sign(key, message) for key, message in zip(private_keys, messages)
]

print(sys.getsizeof(signatures))

agg_sig = bls_pop.Aggregate(signatures)

print(sys.getsizeof(agg_sig))


# Verify aggregate signature with different messages
assert bls_pop.AggregateVerify(
    [
        public_key,
        public_key,
        public_key,
        public_key,
        public_key,
        public_key,
        public_key,
        public_key,
        public_key,
    ],
    messages,
    agg_sig,
)


# from fastecdsa import curve, ecdsa, keys
# from hashlib import sha384
# import sys

# m = "a message to sign via ECDSA"  # some message
# m2 = "a message to sign vasdfsdafsdafia ECDSA"
# m3 = "a message to sign vsadfsafasfia ECDSA"
# m4 = "a message tsadfsafsafo sign via ECDSA"
# m5 = "a message tsdfsfasfo sign via ECDSA"
# m6 = "a message to sigadsfsdafsafn via ECDSA"
# m7 = "a message to sisadfsfsfgn via ECDSA"
# m8 = "a messasdfsfsafge to sign via ECDSA"
# m9 = "a message to sign dsfsfsafsafvia ECDSA"

# """ use default curve and hash function (P256 and SHA2) """
# private_key = keys.gen_private_key(curve.P256)
# public_key = keys.get_public_key(private_key, curve.P256)
# # standard signature, returns two integers
# r, s = ecdsa.sign(m, private_key)
# r, s = ecdsa.sign(m2, private_key)
# r, s = ecdsa.sign(m3, private_key)
# r, s = ecdsa.sign(m4, private_key)
# r, s = ecdsa.sign(m5, private_key)
# r, s = ecdsa.sign(m6, private_key)
# r, s = ecdsa.sign(m7, private_key)
# r, s = ecdsa.sign(m8, private_key)
# r, s = ecdsa.sign(m9, private_key)

# print(sys.getsizeof(r) * 9)
# print(sys.getsizeof(s) * 9)

# # should return True as the signature we just generated is valid.
# valid = ecdsa.verify((r, s), m, public_key)
# valid = ecdsa.verify((r, s), m, public_key)
# valid = ecdsa.verify((r, s), m, public_key)
# valid = ecdsa.verify((r, s), m, public_key)
# valid = ecdsa.verify((r, s), m, public_key)
# valid = ecdsa.verify((r, s), m, public_key)
# valid = ecdsa.verify((r, s), m, public_key)
# valid = ecdsa.verify((r, s), m, public_key)
# valid = ecdsa.verify((r, s), m, public_key)
