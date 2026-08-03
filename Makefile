.PHONY: all clean test otf ttf woff woff2 dist

# Python-based tools (makeotf, otf2ttf, otfautohint, fonttools) come from
# the project venv by default:  python3 -m venv .venv &&
# .venv/bin/pip install -r requirements.txt
# Set TOOLS= (empty) to use tools already on PATH (e.g. in CI).
# ttfautohint and woff2_compress are system packages
# (brew install ttfautohint woff2 / apt install ttfautohint woff2).
TOOLS ?= .venv/bin/

# makeotf shells out to tx/addfeatures/spot, so the tools dir must also
# be on PATH.
ifneq (${TOOLS},)
export PATH := $(abspath ${TOOLS}):${PATH}
endif

ALL_OTFS = $(patsubst ufo/%.ufo,build/otf/%.otf,$(wildcard ufo/*.ufo))
ALL_TTFS = $(patsubst ufo/%.ufo,build/ttf/%.ttf,$(wildcard ufo/*.ufo))
ALL_WOFFS = $(patsubst ufo/%.ufo,build/woff/%.woff,$(wildcard ufo/*.ufo))
ALL_WOFF2S = $(patsubst ufo/%.ufo,build/woff2/%.woff2,$(wildcard ufo/*.ufo))

# Faces shipped in dist/ (DisplayItalic is buildable but not shipped:
# there is no Display Roman for it to accompany).
DIST_FACES = ETBook-Roman ETBook-Italic ETBook-Semibold ETBook-Bold

all: ${ALL_OTFS} ${ALL_TTFS} ${ALL_WOFFS} ${ALL_WOFF2S}

otf: ${ALL_OTFS}
ttf: ${ALL_TTFS}
woff: ${ALL_WOFFS}
woff2: ${ALL_WOFF2S}

clean:
	rm -rf build/ tests/

build:
	mkdir -p build
build/otf: | build
	mkdir -p build/otf
build/ttf: | build
	mkdir -p build/ttf
build/woff: | build
	mkdir -p build/woff
build/woff2: | build
	mkdir -p build/woff2

build/otf/%.otf: ufo/%.ufo ufo/%.ufo/* tools/postprocess.py | build/otf
	${TOOLS}makeotf -nshw -r -f $< -o build/otf/
	${TOOLS}otfautohint $@
	${TOOLS}python tools/postprocess.py $@

build/ttf/%.ttf: build/otf/%.otf | build/ttf
	${TOOLS}otf2ttf -o /dev/stdout $< | ttfautohint /dev/stdin $@

build/woff/%.woff: build/ttf/%.ttf | build/woff
	${TOOLS}fonttools ttLib -o $@ --flavor woff $<

build/woff2/%.woff2: build/ttf/%.ttf | build/woff2
	woff2_compress $< && mv build/ttf/$*.woff2 build/woff2/

dist: $(patsubst %,build/otf/%.otf,${DIST_FACES}) $(patsubst %,build/woff2/%.woff2,${DIST_FACES})
	mkdir -p dist/otf dist/woff2
	cp $(patsubst %,build/otf/%.otf,${DIST_FACES}) dist/otf/
	cp $(patsubst %,build/woff2/%.woff2,${DIST_FACES}) dist/woff2/

HINTING_TEST_SIZES = 14 15 16 17 18 19 20 21

ALL_OTF_HINTING_TESTS = $(patsubst %,tests/otf-hinting/Roman-%.png,${HINTING_TEST_SIZES})
ALL_TTF_HINTING_TESTS = $(patsubst %,tests/ttf-hinting/Roman-%.png,${HINTING_TEST_SIZES})

test: ${ALL_OTF_HINTING_TESTS} ${ALL_TTF_HINTING_TESTS}

tests:
	mkdir -p tests
tests/otf-hinting: | tests
	mkdir -p tests/otf-hinting
tests/ttf-hinting: | tests
	mkdir -p tests/ttf-hinting

tests/otf-hinting/Roman-%.png: build/otf/ETBook-Roman.otf | tests/otf-hinting
	convert -background white -fill black -font build/otf/ETBook-Roman.otf -pointsize $* label:'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ß' $@

tests/ttf-hinting/Roman-%.png: build/ttf/ETBook-Roman.ttf | tests/ttf-hinting
	convert -background white -fill black -font build/ttf/ETBook-Roman.ttf -pointsize $* label:'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ ß' $@
