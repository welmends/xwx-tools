# xwx-tools

Caixa de ferramentas de linha de comando instalável via `pip`. Um pacote, vários comandos —
cada script vira um executável próprio no seu PATH.

| Comando  | O que faz |
| -------- | --------- |
| `gcpuse` | Troca de contexto GCP (gcloud CLI + ADC do Terraform) por configuration nomeada |

## Instalação

Recomendado (isolado, sem sujar o Python do sistema):

```bash
pipx install xwx-tools
```

Ou, num virtualenv qualquer:

```bash
pip install xwx-tools
```

Atualizar: `pipx upgrade xwx-tools` (ou `pip install -U xwx-tools`).

## gcpuse

Requer o [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`) no PATH.

```bash
gcpuse                    # em qual configuration / conta / projeto estou?
gcpuse --list             # lista as configurations disponíveis (* = ativa)
gcpuse staging            # ativa 'staging' e refaz o login (CLI + ADC)
gcpuse staging --no-login # só troca de configuration, sem login
gcpuse staging --no-adc   # login da CLI, sem refazer a ADC
```

`gcpuse <nome>` faz, em ordem:

1. `gcloud config configurations activate <nome>`
2. `gcloud auth login` — credenciais da CLI
3. `gcloud auth application-default login` — ADC, que é o que o Terraform usa
4. `gcloud auth application-default set-quota-project <projeto da configuration>`

Códigos de saída: `0` ok, `1` erro do gcloud (ou configuration inexistente),
`127` gcloud não instalado, `130` cancelado com Ctrl-C.

### Criando uma configuration

```bash
gcloud config configurations create staging
gcloud config set project meu-projeto-staging
```

## Desenvolvimento

```bash
uv venv && uv pip install -e ".[dev]"
.venv/bin/python -m pytest
.venv/bin/python -m ruff check .
```

## Adicionando uma ferramenta nova

1. Crie `src/xwx/cli/minhaferramenta.py` com uma função `main(argv=None) -> int`.
2. Registre em `pyproject.toml`:

   ```toml
   [project.scripts]
   minhaferramenta = "xwx.cli.minhaferramenta:main"
   ```

3. Coisas reaproveitáveis (execução de processos, saída no terminal, wrappers de CLIs
   externas) vão para `src/xwx/core/`.
4. Testes em `tests/`, bump da versão em `src/xwx/__init__.py`, tag `vX.Y.Z` → o CI publica.

## Publicando uma versão

O workflow `.github/workflows/publish.yml` publica no PyPI via
[Trusted Publishing](https://docs.pypi.org/trusted-publishers/) quando você empurra uma tag
`v*`. Configure uma vez em pypi.org → *Publishing*: owner `welmends`, repo `xwx-tools`,
workflow `publish.yml`, environment `pypi`.

```bash
# edita __version__ e CHANGELOG.md
git tag v0.1.0 && git push origin v0.1.0
```

## Licença

MIT — veja [LICENSE](LICENSE).
