TEST_DIR := tests

test:
	uv run pytest ${TEST_DIR}

.PHONY: test
