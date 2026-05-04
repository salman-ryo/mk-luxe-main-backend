.PHONY: build start

# Called during Render's Build Step
build:
	@bash ./build.sh

# Called during Render's Start Step
start:
	@bash ./start.sh