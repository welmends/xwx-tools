# Changelog

Formato baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.1.0/);
versionamento [SemVer](https://semver.org/lang/pt-BR/).

## [Não lançado]

## [0.1.0] - 2026-08-18

### Adicionado

- `gcpuse`: status do contexto GCP, `--list`, troca de configuration com login
  da CLI + ADC e alinhamento do quota project da ADC.
- Flags `--no-login` e `--no-adc` para trocar de configuration sem refazer login.
- Estrutura do pacote `xwx` (`xwx.cli` para comandos, `xwx.core` para código
  compartilhado) e workflows de CI e publicação no PyPI.
