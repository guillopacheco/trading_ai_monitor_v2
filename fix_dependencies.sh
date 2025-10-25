#!/bin/bash
echo "🔧 REPARANDO CONFLICTOS DE DEPENDENCIAS..."

source venv/bin/activate

echo "📦 Reinstalando numpy compatible..."
python -m pip install numpy==1.26.4 --force-reinstall

echo "📦 Verificando scipy..."
python -c "import scipy; print('✅ scipy - OK')"

echo "📦 Verificando pandas-ta..."
python -c "
import pandas_ta as ta
import pandas as pd
import numpy as np

df = pd.DataFrame({'close': [1,2,3,4,5]})
rsi = ta.rsi(df['close'])
print('✅ pandas-ta - OK')
print(f'   numpy: {np.__version__}')
print(f'   pandas: {pd.__version__}')
print(f'   RSI test: {rsi.iloc[-1]}')
"

echo "🎯 DEPENDENCIAS REPARADAS!"
