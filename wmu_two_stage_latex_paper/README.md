# WMU Two-Stage LaTeX Paper

VS Code에서 이 폴더를 열고 `main.tex`를 편집하시면 됩니다. 이 폴더는 **VS Code + LaTeX Workshop + TinyTeX/TeX Live + latexmk** 기준으로 세팅되어 있습니다.

## 1. 폴더 열기

```bash
code /home/hy/WMU_project/wmu_two_stage_latex_paper
```

또는 파일 관리자에서 이 폴더를 열고, 우클릭/터미널에서 VS Code를 실행하셔도 됩니다.

## 2. 작업 방식

1. VS Code에서 `main.tex`를 엽니다.
2. 오른쪽 위 또는 왼쪽 Activity Bar의 **TeX** 아이콘을 누릅니다.
3. 기본 recipe는 `latexmk (xelatex)`입니다.
4. 저장하면 자동 빌드됩니다.
5. 생성 PDF는 아래에 생깁니다.

```text
build/main.pdf
```

## 3. 수동 빌드

```bash
cd /home/hy/WMU_project/wmu_two_stage_latex_paper
latexmk -xelatex -interaction=nonstopmode -file-line-error -synctex=1 -outdir=build main.tex
```

## 4. 필요한 프로그램/확장

이미 세팅 완료:

- VS Code
- VS Code Extension: `james-yu.latex-workshop`
- TinyTeX / TeX Live 2026: `/home/hy/.TinyTeX`
- `latexmk`
- `xelatex`
- `bibtex`
- `biber`
- `kotex`, `xetexko`
- IEEEtran, siunitx, pgfplots, booktabs 등 논문용 패키지

## 5. Files

- `main.tex`: IEEE conference 형식 LaTeX 논문 초안
- `references.bib`: BibTeX reference database
- `figures/`: Fig. 1--Fig. 6 PDF/PNG figure source
- `.vscode/settings.json`: LaTeX Workshop recipe
- `build/main.pdf`: 컴파일된 PDF

## 6. Included figures

- Fig. 1 Proposed two-stage framework
- Fig. 2 Detection confusion matrix for Bus 27
- Fig. 3 Minimum WMU count for zone localization
- Fig. 4 Selected 8-WMU placement on IEEE 30-bus topology
- Fig. 5 Zone localization confusion matrix
- Fig. 6 Current disturbance argmax explanation
