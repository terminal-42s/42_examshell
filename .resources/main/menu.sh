#!/bin/bash

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

clear
# permisson
find "$SCRIPT_DIR/../rank02/level0" -name "tester.sh" -exec chmod +x {} \;
find "$SCRIPT_DIR/../rank02/level1" -name "tester.sh" -exec chmod +x {} \;
find "$SCRIPT_DIR/../rank02/level2" -name "tester.sh" -exec chmod +x {} \;
find "$SCRIPT_DIR/../rank02/level3" -name "tester.sh" -exec chmod +x {} \;
find "$SCRIPT_DIR/../rank03/level1" -name "tester.sh" -exec chmod +x {} \;
find "$SCRIPT_DIR/../rank03/level2" -name "tester.sh" -exec chmod +x {} \;
find "$SCRIPT_DIR/../rank04/level1" -name "tester.sh" -exec chmod +x {} \;
find "$SCRIPT_DIR/../rank04/level2" -name "tester.sh" -exec chmod +x {} \;
find "$SCRIPT_DIR/../rank05/level1" -name "tester.sh" -exec chmod +x {} \;
find "$SCRIPT_DIR/../rank05/level2" -name "tester.sh" -exec chmod +x {} \;
find "$SCRIPT_DIR/../rank06" -name "tester.sh" -exec chmod +x {} \;

bash label.sh
bash intro.sh
