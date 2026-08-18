import json
from pathlib import Path


EXPECTED = {
    "audio_drive.json", "chain_section.json", "i2v.json", "image.json", "keyframes.json",
    "r2v.json", "t2v.json", "upscale.json", "upscale_rtx.json", "video_extend.json",
}
PLACEHOLDERS = {"chain_section.json": {"sec:previmg", "sec:ctxlat"}}


def main():
    root = Path(__file__).resolve().parents[1] / "workflows"
    files = {path.name for path in root.glob("*.json")}
    if files != EXPECTED:
        raise AssertionError(f"workflow set changed: expected {sorted(EXPECTED)}, got {sorted(files)}")
    for path in sorted(root.glob("*.json")):
        workflow = json.loads(path.read_text(encoding="utf-8-sig"))
        if not isinstance(workflow, dict) or not workflow:
            raise AssertionError(f"{path.name}: workflow must be a non-empty object")
        for node_id, node in workflow.items():
            if not isinstance(node, dict) or not isinstance(node.get("class_type"), str) or not isinstance(node.get("inputs"), dict):
                raise AssertionError(f"{path.name}: malformed node {node_id}")
            for key, value in node["inputs"].items():
                if isinstance(value, list) and len(value) == 2 and isinstance(value[0], str) and isinstance(value[1], int):
                    if value[0] not in workflow and value[0] not in PLACEHOLDERS.get(path.name, set()):
                        raise AssertionError(f"{path.name}: missing link target {node_id}.{key} -> {value}")
    print("10 workflow templates valid")


if __name__ == "__main__":
    main()
