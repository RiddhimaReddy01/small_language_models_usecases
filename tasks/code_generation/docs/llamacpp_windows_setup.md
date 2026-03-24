# llama.cpp Windows Setup

This project now supports a `llama_cpp` backend, but this machine does not currently have the native Windows toolchain needed to build `llama-cpp-python` from source.

## Current status

- `winget` is available.
- `cmake` is not installed.
- Visual C++ build tools are not installed.
- The published `llama-cpp-python-win` wheel currently available on PyPI is `cp314`, which does not match the Python `3.11` and `3.13` interpreters on this machine.

## Recommended install path

Run:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_llamacpp_windows.ps1
```

The script will:

1. Install `Kitware.CMake` with `winget` if needed.
2. Install `Microsoft.VisualStudio.2022.BuildTools` with the C++ workload if needed.
3. Load `vcvars64.bat`.
4. Install `llama-cpp-python` into the selected Python environment.

## Optional flags

Use a specific interpreter:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_llamacpp_windows.ps1 -PythonExe "py -3.13"
```

Skip build-tools installation if they are already present:

```powershell
powershell -ExecutionPolicy Bypass -File .\install_llamacpp_windows.ps1 -SkipBuildToolsInstall
```

## After install

Verify the binding:

```powershell
python -c "from llama_cpp import Llama; print('llama.cpp ready')"
```

Then run one of the new configs such as:

```powershell
python -m codegen_eval --config "llamacpp_qwen05_q4_tiny.json"
```
