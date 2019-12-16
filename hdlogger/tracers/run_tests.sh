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
