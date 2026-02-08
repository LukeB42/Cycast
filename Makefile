.PHONY: build clean run install test help rebuild

help:
	@echo "Cycast - Icecast-Compatible Streaming Server"
	@echo ""
	@echo "Available commands:"
	@echo "  make install    - Install Python dependencies"
	@echo "  make build      - Build Cython extensions"
	@echo "  make rebuild    - Clean and rebuild Cython extensions"
	@echo "  make run        - Run the server"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make test       - Test the Cython modules"
	@echo ""

install:
	pip install -r requirements.txt

build:
	python setup.py build_ext --inplace
	@echo ""
	@echo "Build complete! Cython modules compiled."
	@echo ""

rebuild: clean build
	@echo ""
	@echo "Rebuild complete!"
	@echo ""

run: build
	python cycast_server.py

clean:
	rm -rf build/
	rm -f *.so *.c *.pyd
	rm -rf __pycache__/
	rm -rf *.egg-info/
	find . -name "*.pyc" -delete
	@echo "Cleaned build artifacts"

test: build
	python -c "import audio_buffer; print('✓ audio_buffer module OK')"
	python -c "import stream_broadcaster; print('✓ stream_broadcaster module OK')"
	python -c "import config_loader; print('✓ config_loader module OK')"
	python -c "import flask_app; print('✓ flask_app module OK')"
	@echo ""
	@echo "All modules loaded successfully!"
	@echo ""
