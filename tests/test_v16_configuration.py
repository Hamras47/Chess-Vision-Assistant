import ast
from pathlib import Path
from app.ai.openai_client import DEFAULT_OPENAI_VISION_MODEL,OpenAIClient,resolve_model

ROOT=Path(__file__).parents[1]

def test_model_configuration_precedence_and_exact_api_model(monkeypatch):
    assert DEFAULT_OPENAI_VISION_MODEL=='gpt-5.6-terra'
    assert resolve_model('',{})=='gpt-5.6-terra'
    assert resolve_model('',{'OPENAI_VISION_MODEL':'gpt-5.6-terra'})=='gpt-5.6-terra'
    assert resolve_model('unsupported',{'OPENAI_VISION_MODEL':'gpt-5.6-terra'})=='gpt-5.6-terra'
    assert resolve_model('gpt-5.6-luna',{'OPENAI_VISION_MODEL':'gpt-5.6-terra'})=='gpt-5.6-luna'
    assert OpenAIClient('gpt-5.6-luna').model=='gpt-5.6-luna'

def test_runtime_has_no_ml_imports_or_dependencies():
    forbidden={'torch','torchvision','onnx','onnxruntime','sklearn'}
    for source in (ROOT/'app').rglob('*.py'):
        tree=ast.parse(source.read_text(encoding='utf-8'))
        names={node.names[0].name.split('.')[0] for node in ast.walk(tree) if isinstance(node,ast.Import)}
        names|={node.module.split('.')[0] for node in ast.walk(tree) if isinstance(node,ast.ImportFrom) and node.module}
        assert not names & forbidden, source
    assert 'classifier.py' not in {path.name for path in (ROOT/'app').rglob('*.py')}
    project=(ROOT/'pyproject.toml').read_text(encoding='utf-8').lower()
    assert not any(name in project for name in forbidden)
