TEST_DIR := tests

test:
	uv run pytest ${TEST_DIR}

build:
	uv build

install:
	uv pip install git+https://github.com/dagsdags212/biocurator.git

.PHONY: test build install
