# CAIROS

**CAIROS — Context-Aware Intelligent Runtime Operating Shell**

CAIROS is a context-aware command assistant that lives inside your normal shell. It is **not** a replacement for zsh, bash or fish. You install it as a normal console command and use it while working inside any project directory.

```bash
cairos macke python projekt demo mit venv git pytest
cairos create cpp header file Player
cairos make folder docs
cairos explain git reset --soft HEAD~1
cairos config ai use-ollama llama3.1
```

CAIROS first tries deterministic templates with typo-tolerant matching. Only when it cannot solve a request locally does it fall back to a configured AI backend.

## Quick start for development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
cairos --version
make test
```

## Install as a console helper

From a checkout:

```bash
python -m pip install .
```

For a user-level isolated install, use `pipx`:

```bash
pipx install .
```

After installation, `cairos` can be used from any folder.

## Local AI setup

```bash
cairos config ai use-ollama llama3.1
ollama pull llama3.1
ollama serve
```

## API setup

```bash
export OPENAI_API_KEY="your-key"
cairos config ai use-openai gpt-4.1-mini
```

See [`DOCUMENTATION.md`](DOCUMENTATION.md) for full commands, settings and behavior.
