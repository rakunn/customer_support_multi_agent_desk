import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.db.seed import demo_store


def main() -> None:
    demo_store.reset()
    print(
        "Loaded "
        f"{len(demo_store.customers)} customers and "
        f"{len(demo_store.orders)} orders into the demo store."
    )


if __name__ == "__main__":
    main()
