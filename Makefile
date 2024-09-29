.PHONY: install run clean

# Install dependencies
install:
	python3 -m venv venv && . venv/bin/activate && pip install -r requirements.txt

# Run the main script using the correct environment
run:
	. venv/bin/activate && ./wvtbl.sh

# Clean temporary files and output wavetables
clean:
	rm -rf venv
	rm -rf wavetables
	find src/ -name '*.pyc' -delete
