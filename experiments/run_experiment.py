import json
from pathlib import Path

from cv_extraction.pipeline import run_extraction


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def main():
    pdf_path = (
        PROJECT_ROOT
        / "data"
        / "cvs"
        / "CV001_altacv_sample.pdf"
    )

    result = run_extraction(pdf_path)

    print(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()