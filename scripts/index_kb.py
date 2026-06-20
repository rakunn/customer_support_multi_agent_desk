import json

from app.config import get_settings
from app.services.rag_service import load_knowledge_base


def main() -> None:
    settings = get_settings()
    settings.vector_db_dir.mkdir(parents=True, exist_ok=True)
    chunks = load_knowledge_base()
    output_path = settings.vector_db_dir / "kb_index.json"
    output_path.write_text(
        json.dumps([chunk.__dict__ for chunk in chunks], indent=2),
        encoding="utf-8",
    )
    print(f"Indexed {len(chunks)} knowledge-base chunks at {output_path}.")


if __name__ == "__main__":
    main()

