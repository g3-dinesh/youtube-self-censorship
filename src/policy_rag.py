import argparse
import json
import os
import sys
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
CORPUS_DIR = os.path.join(HERE, "..", "data", "policy_corpus")
DEFAULT_CHUNKS = os.path.join(CORPUS_DIR, "chunks.jsonl")
DEFAULT_INDEX = os.path.join(CORPUS_DIR, "index.npz")
DEFAULT_META = os.path.join(CORPUS_DIR, "index.meta.json")
DEFAULT_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_EMBED_MODEL = "nomic-embed-text"


def load_chunks(path):
    recs = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                recs.append(json.loads(line))
    return recs


def embed_texts(host, model, texts, batch=32, timeout=120):
    url = host.rstrip("/") + "/api/embed"
    out = []
    for i in range(0, len(texts), batch):
        chunk = texts[i:i + batch]
        body = json.dumps({"model": model, "input": chunk}).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        embs = data.get("embeddings")
        if not embs:
            raise RuntimeError(f"no embeddings returned (got keys {list(data)})")
        out.extend(embs)
    arr = np.asarray(out, dtype=np.float32)
    norms = np.linalg.norm(arr, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return arr / norms


def build_index(chunks_path, host, model, index_path, meta_path):
    recs = load_chunks(chunks_path)
    if not recs:
        raise SystemExit(f"no chunks in {chunks_path}")
    vecs = embed_texts(host, model, [r["text"] for r in recs])
    np.savez_compressed(index_path, vectors=vecs,
                        ids=np.array([r["id"] for r in recs]))
    with open(meta_path, "w", encoding="utf-8") as fh:
        json.dump({"model": model, "records": recs}, fh, ensure_ascii=False)
    return len(recs), vecs.shape[1]


def load_index(index_path, meta_path):
    npz = np.load(index_path, allow_pickle=False)
    with open(meta_path, encoding="utf-8") as fh:
        meta = json.load(fh)
    return npz["vectors"], meta["records"], meta.get("model", DEFAULT_EMBED_MODEL)


def retrieve(query, vectors, records, host, model, k=4):
    q = embed_texts(host, model, [query])[0]
    scores = vectors @ q
    order = np.argsort(-scores)[:k]
    return [(records[i], float(scores[i])) for i in order]


def format_hit(rec, score):
    lines = [f"[{score:.3f}] {rec['category']}  ({rec['source']})",
             f"    rule: {rec['rule']}"]
    for key, label in (("monetizable", "monetize"),
                       ("limited", "limited"),
                       ("no_ads", "no ads")):
        if rec.get(key):
            lines.append(f"    {label}: {rec[key]}")
    lines.append(f"    source: {rec['source_url']} (retrieved {rec['retrieved']})")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(
        description="Policy RAG over the YouTube monetisation policy corpus: "
                    "embed the corpus with an Ollama embedding model and "
                    "retrieve the policy sections most relevant to a query.")
    sub = ap.add_subparsers(dest="cmd", required=True)

    b = sub.add_parser("build", help="embed the corpus and write the index")
    b.add_argument("--chunks", default=DEFAULT_CHUNKS)
    b.add_argument("--index", default=DEFAULT_INDEX)
    b.add_argument("--meta", default=DEFAULT_META)
    b.add_argument("--host", default=DEFAULT_HOST)
    b.add_argument("--model", default=DEFAULT_EMBED_MODEL)

    q = sub.add_parser("query", help="retrieve policy sections for a query")
    q.add_argument("text", help="the query text")
    q.add_argument("-k", type=int, default=4)
    q.add_argument("--index", default=DEFAULT_INDEX)
    q.add_argument("--meta", default=DEFAULT_META)
    q.add_argument("--host", default=DEFAULT_HOST)

    args = ap.parse_args()

    if args.cmd == "build":
        try:
            n, dim = build_index(args.chunks, args.host, args.model,
                                 args.index, args.meta)
        except urllib.error.URLError as e:
            sys.exit(f"could not reach Ollama at {args.host}: {e}\n"
                     "Is the SSH tunnel open and 'nomic-embed-text' pulled?")
        print(f"-> {args.index}  ({n} chunks, dim {dim}, model {args.model})")
    elif args.cmd == "query":
        if not (os.path.exists(args.index) and os.path.exists(args.meta)):
            sys.exit("no index found; run 'policy_rag.py build' first")
        vecs, recs, model = load_index(args.index, args.meta)
        try:
            hits = retrieve(args.text, vecs, recs, args.host, model, args.k)
        except urllib.error.URLError as e:
            sys.exit(f"could not reach Ollama at {args.host}: {e}")
        for rec, score in hits:
            print(format_hit(rec, score))
            print()


if __name__ == "__main__":
    main()
