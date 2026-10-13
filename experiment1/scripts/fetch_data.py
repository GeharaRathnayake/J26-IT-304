"""Download JavaQuestionSynthFinal at the pinned revision into data/raw."""

from confusion_baseline.data import DATASET_REPO, DATASET_REVISION, fetch


def main() -> None:
    path = fetch()
    print("repo:    ", DATASET_REPO)
    print("revision:", DATASET_REVISION)
    print("local:   ", path)
    print("files written:")
    for f in sorted(p for p in path.rglob("*") if p.is_file() and ".cache" not in p.parts):
        print(f"  {f.relative_to(path).as_posix()}  ({f.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
