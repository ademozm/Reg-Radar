import os
import sys

# tests/ klasörü kökten ayrı olduğu için, testlerin `import lynch_strategy`,
# `import config` gibi kök seviyesindeki modülleri bulabilmesi için kökü
# sys.path'e ekliyoruz.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
