import sys
sys.path.insert(0, "src")
from timelink_score.score_embed.compressor import compress_score, decompress_score

data = {"melody": [{"s": 0.5, "d": 0.5, "m": 60, "conf": 0.9}] * 100}
import json
json_str = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
enc = compress_score(data)
print(f"원본: {len(json_str)} bytes")
print(f"압축: {len(enc)} bytes")
print(f"압축률: {100*len(enc)/len(json_str):.1f}%")
dec = decompress_score(enc)
assert dec == data, "왕복 실패"
print("왕복 OK")