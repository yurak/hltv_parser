# Стаття 3 -> видання №69 (Вісник ЛНУ). Збирання: pdflatex (шаблон VISNYK2019 на T2A).
TEX = pdflatex -interaction=nonstopmode -halt-on-error

all: article.pdf

article.pdf: article.tex VisnykAMI.tex $(wildcard figures/*.pdf)
	$(TEX) article.tex
	$(TEX) article.tex

clean:
	rm -f article.aux article.log article.out article.toc article.dvi

distclean: clean
	rm -f article.pdf

.PHONY: all clean distclean
