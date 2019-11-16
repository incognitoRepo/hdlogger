python -m unittest -v
FILES=(
  'DEtrace'
  'DEpdb'
  'DEbdb'
  'DEsmiley'
)
files=$(print test_${^FILES}.py)

for file in $files; do
  python -m unittest -v $file
done


python /Users/alberthan/.vscode-insiders/extensions/ms-python.python-2019.12.48501-dev/pythonFiles/testing_tools/run_adapter.py discover pytest -- -s --trace-config --cache-clear -c /Users/alberthan/.dotfiles/python/pytest.ini
python /Users/alberthan/.vscode-insiders/extensions/ms-python.python-2019.12.48501-dev/pythonFiles/testing_tools/run_adapter.py discover pytest -- -c /Users/alberthan/.dotfiles/python/pytest.ini
