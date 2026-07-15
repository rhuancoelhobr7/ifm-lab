#!/usr/bin/env python3
"""
check_tarefas.py — validador da lista de tarefas da pesquisa (PLANO §1.3 e §2).

💡 O que este script faz, em linguagem simples: ele é o "fiscal" que roda antes
de todo commit e garante três coisas — (1) nenhuma tarefa foi marcada como
concluída sem uma prova que exista de verdade (arquivo no repo ou commit);
(2) nenhum trabalho foi feito "pulando a fila" de um portão que o dono da
pesquisa ainda não carimbou; (3) todo relatório de resultado usado como prova
segue o template didático (§1.2): tem as seções obrigatórias, toda tabela e
figura vem seguida de uma linha "**Leitura:**", e o confronto cita os critérios
C1–C11. Se qualquer regra falhar, o script sai com erro e o commit não acontece.

Uso:
    python scripts/check_tarefas.py            # valida TAREFAS.md + evidências
    python scripts/check_tarefas.py --all      # também valida TODOS os results/E*.md
Saída: relatório no stdout; código de saída 0 = ok, 1 = violações.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

RESEARCH_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = RESEARCH_DIR.parent.parent

TAREFAS = RESEARCH_DIR / "TAREFAS.md"
PROGRESS = RESEARCH_DIR / "PROGRESS.md"

# Seções obrigatórias do template didático (PLANO §1.2)
SECOES_OBRIGATORIAS = [
    "## O que perguntamos",
    "## Como testamos",
    "## Resultados",
    "## Confronto com os critérios",
    "## O que isso muda",
    "## Limitações",
]

RE_CHECKBOX = re.compile(r"^\s*-\s\[([ x~!\-])\]\s+(.*)$")
RE_EVIDENCIA = re.compile(r"\(([^()]*)\)\s*$")
RE_HASH = re.compile(r"^[0-9a-f]{7,40}$")
RE_PORTAO = re.compile(r"🚪\s*(P\d[ab]?)")
RE_CRITERIO = re.compile(r"\bC\d{1,2}\b")
RE_RESULT_MD = re.compile(r"results/E\d+\w*.*\.md$")


def eh_commit_valido(token: str) -> bool:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--verify", "--quiet", token + "^{commit}"],
            cwd=REPO_ROOT, capture_output=True, text=True,
        )
        return r.returncode == 0
    except OSError:
        return False


def resolve_evidencia(token: str) -> bool:
    """Evidência válida = arquivo existente (relativo à pesquisa ou ao repo) ou hash de commit."""
    token = token.strip()
    if not token:
        return False
    if RE_HASH.match(token):
        return eh_commit_valido(token)
    return (RESEARCH_DIR / token).exists() or (REPO_ROOT / token).exists()


def valida_template_didatico(path: Path) -> list[str]:
    """Valida um results/EXX_*.md contra o template do PLANO §1.2."""
    erros: list[str] = []
    rel = path.relative_to(RESEARCH_DIR) if path.is_relative_to(RESEARCH_DIR) else path
    texto = path.read_text(encoding="utf-8")
    linhas = texto.splitlines()

    for secao in SECOES_OBRIGATORIAS:
        if not any(l.strip().lower().startswith(secao.lower()) for l in linhas):
            erros.append(f"{rel}: seção obrigatória ausente: '{secao}'")

    # Toda tabela (bloco de linhas iniciando com '|') e toda imagem ('![')
    # deve ser seguida, em até 3 linhas não vazias, por '**Leitura:**'.
    def leitura_apos(idx: int) -> bool:
        vistas = 0
        for l in linhas[idx + 1:]:
            s = l.strip()
            if not s:
                continue
            vistas += 1
            if s.startswith("**Leitura:**"):
                return True
            if vistas >= 3:
                break
        return False

    i = 0
    while i < len(linhas):
        if linhas[i].strip().startswith("|"):
            fim = i
            while fim + 1 < len(linhas) and linhas[fim + 1].strip().startswith("|"):
                fim += 1
            if not leitura_apos(fim):
                erros.append(f"{rel}:{i + 1}: tabela sem linha '**Leitura:**' logo após")
            i = fim + 1
            continue
        if "![" in linhas[i] and not leitura_apos(i):
            erros.append(f"{rel}:{i + 1}: figura sem linha '**Leitura:**' logo após")
        i += 1

    # O confronto precisa citar ao menos um código C_n
    m = re.search(r"## Confronto com os critérios(.*?)(\n## |\Z)", texto, re.S | re.I)
    if m and not RE_CRITERIO.search(m.group(1)):
        erros.append(f"{rel}: 'Confronto com os critérios' não cita nenhum código C1–C11")

    return erros


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--all", action="store_true",
                    help="valida também todos os results/E*.md, mesmo não citados como evidência")
    args = ap.parse_args()

    erros: list[str] = []

    if not TAREFAS.exists():
        print(f"ERRO: {TAREFAS} não encontrado.")
        return 1
    progress_txt = PROGRESS.read_text(encoding="utf-8") if PROGRESS.exists() else ""

    portoes_pendentes: list[str] = []   # portões ainda não carimbados, na ordem do arquivo
    evidencias_md: set[Path] = set()

    for num, linha in enumerate(TAREFAS.read_text(encoding="utf-8").splitlines(), 1):
        m = RE_CHECKBOX.match(linha)
        if not m:
            continue
        estado, texto = m.group(1), m.group(2)
        portao = RE_PORTAO.search(texto)

        if estado == "x":
            # Regra: nada concluído depois de um portão anterior pendente
            if portoes_pendentes:
                erros.append(
                    f"TAREFAS.md:{num}: tarefa [x] com portão anterior pendente "
                    f"({', '.join(portoes_pendentes)}): {texto[:60]}"
                )
            # Regra: [x] exige evidência verificável
            ev = RE_EVIDENCIA.search(texto)
            if not ev:
                erros.append(f"TAREFAS.md:{num}: tarefa [x] sem evidência entre parênteses: {texto[:60]}")
            else:
                cru = ev.group(1)
                cru = re.sub(r"^\s*evid[êe]ncia:\s*", "", cru, flags=re.I)
                tokens = [t for t in re.split(r"[,;+]\s*", cru) if t.strip()]
                if not tokens:
                    erros.append(f"TAREFAS.md:{num}: evidência vazia: {texto[:60]}")
                for t in tokens:
                    if not resolve_evidencia(t):
                        erros.append(f"TAREFAS.md:{num}: evidência não encontrada no repo: '{t.strip()}'")
                    elif RE_RESULT_MD.search(t.strip()):
                        p = (RESEARCH_DIR / t.strip())
                        evidencias_md.add(p if p.exists() else (REPO_ROOT / t.strip()))
            # Regra: portão [x] exige decisão registrada no PROGRESS.md
            if portao and portao.group(1) not in progress_txt:
                erros.append(
                    f"TAREFAS.md:{num}: portão {portao.group(1)} marcado [x] sem decisão "
                    f"registrada no PROGRESS.md"
                )
        elif portao:  # portão não concluído → bloqueia [x] dali em diante
            portoes_pendentes.append(portao.group(1))

        if estado in "!-" and "(" not in texto:
            erros.append(f"TAREFAS.md:{num}: tarefa [{estado}] sem motivo entre parênteses: {texto[:60]}")

    # Conformidade didática (§1.2) dos relatórios usados como evidência
    alvos = set(evidencias_md)
    if args.all:
        alvos |= set((RESEARCH_DIR / "results").glob("E*.md"))
    for p in sorted(alvos):
        if p.exists():
            erros.extend(valida_template_didatico(p))

    if erros:
        print(f"✘ check_tarefas: {len(erros)} violação(ões):\n")
        for e in erros:
            print(f"  - {e}")
        print("\nCommit BLOQUEADO até corrigir (PLANO §1.3 e §2).")
        return 1

    print("✔ check_tarefas: TAREFAS.md consistente — evidências existem, "
          "portões respeitados, relatórios no template didático.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
