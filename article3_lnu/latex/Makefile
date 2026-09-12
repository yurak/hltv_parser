# Стаття 3 -> видання №69 (Вісник ЛНУ). Збирання: pdflatex (шаблон VISNYK2019 на T2A).
#   article_en.pdf — ВЕРСІЯ ДЛЯ ПОДАННЯ (англійський текст, українські метадані)
#   article.pdf    — довідкова українська версія
TEX = pdflatex -interaction=nonstopmode -halt-on-error
FIGS_UK = $(wildcard figures/*.pdf)
FIGS_EN = $(wildcard figures_en/*.pdf)

all: article_en.pdf article.pdf

en: article_en.pdf
uk: article.pdf

article_en.pdf: article_en.tex VisnykAMI.tex $(FIGS_EN)
	$(TEX) article_en.tex
	$(TEX) article_en.tex

article.pdf: article.tex VisnykAMI.tex $(FIGS_UK)
	$(TEX) article.tex
	$(TEX) article.tex

clean:
	rm -f *.aux *.log *.out *.toc *.dvi

distclean: clean
	rm -f article.pdf article_en.pdf

.PHONY: all en uk clean distclean

# Друкований пакет для наукового керівника (він читає на папері, не в GitHub).
#   make report      -> review/compliance_report_en.pdf   (звіт про відповідність, 3 с.)
#   make supervisor  -> review/supervisor_package_en.pdf  (звіт + сама стаття, один файл на друк)
report:
	cd .. && python3 scripts/check_compliance.py en --pdf

supervisor: report article_en.pdf
	pdfunite ../review/compliance_report_en.pdf article_en.pdf ../review/supervisor_package_en.pdf
	@echo "на друк: review/supervisor_package_en.pdf"

.PHONY: report supervisor
