"""
Copyright (c) 2024 Steven Koe and Tan Chuan Hong Algene

All rights reserved.

This code and any works derived from it are owned by Steven Koe and Tan Chuan Hong Algene.
Permission must be obtained from Steven Koe and Tan Chuan Hong Algene to use, modify, distribute, sell, 
or create derivative works from this code.

Contact Information:
Steven Koe - steven.koe80@gmail.com
Tan Chuan Hong Algene - hydrater@gmail.com

Any unauthorized use, modification, distribution, sale, or creation of derivative works is strictly prohibited.

"""
# from strategy.strategy_Straight import Strategy_Straight
# from strategy.strategy_chameleon_no_print import ChameleonNoPrint
# from strategy.strategy_phoenix import Phoenix
# from strategy.strategy_example import StrategyExample
# from strategy.strategy_time_based import StrategyTimeBased
# from strategy.strategy_test_functions import Test_functions
# from strategy.strategy_turnaround_tuesdays import TurnaroundTuesdays
# from strategy.strategy_turnaround_tuesdaysV2 import TurnaroundTuesdaysV2
# from strategy.strategy_long_3_leverage import StrategyLongLeverage
# from strategy.strategy_turnaround_daybreak import TurnaroundDaybreak
# from strategy.strategy_turnaround_daybreakV2 import TurnaroundDaybreakV2
# from strategy.strategy_twinbreak import TwinBreak
# from strategy.strategy_turnaround_daybreak_fix import TurnaroundDaybreakFix
# from strategy.strategy_twinbreak_legacy import TwinBreakLegacy
# from strategy.strategy_turnaround_shortbreak import TurnaroundShortbreak
# from strategy.strategy_turnaround_daybreak_stoploss import TurnaroundStopLoss
# from strategy.strategy_turnaround_onlyshorts import TurnaroundOnlyshorts
# from strategy.c_lab import C_Lab
# from strategy.strategy_chadaybreak import Chadaybreak
# from strategy.strategy_chameleon_tracked import Chameleon as Tracked
# from strategy.c_lab_2 import C_Lab as C_Lab_2
# from strategy.strategy_chameleon_evolved import Chameleon as Evolved
# from strategy.strategy_day_trade import StrategyDay
from strategy.strategy_chameleon import Chameleon
# from strategy.strategy_MA import StrategyMA as MA
# from strategy.strategy_0dte_iron_bf import iron_bf as IBF
# from strategy.strategy_0dte_ibf_bt import iron_bf as IBF_BT
#from strategy.strategy_chameleon_V2 import ChameleonV2
from strategy.strategy_0dte_hyper_bf import hyper_bf as HyperBF
from strategy.strategy_0dte_hbf_live import hyper_bf as HyperBF_Live
from strategy.strategy_0dte_hbf_lab import hyper_bf as HyperBF_Lab
from strategy.strategy_0dte_hyper_bf_hedged import hyper_bf as HyperBF_Hedged
from strategy.strategy_candlestick_test import candlestick_test as CandleStick_Test
from strategy.strategy_0dte_golden_bf import golden_butterfly as GoldenBF
from strategy.strategy_0dte_golden_bf_old import golden_bf as GoldenBF_Old
from strategy.strategy_0dte_oroboros import oroboros as Orobros
from strategy.strategy_0dte_gbf_live import golden_butterfly as GoldenBF_Live
from strategy.strategy_0dte_inverse_gbf import inverse_gbf as Inverse_GBF

def get_strategy(strategy_name):
    match (strategy_name):
        # case 'strategy_example':
        #     return StrategyExample()
        # case 'straight':
        #     return Strategy_Straight()
        # case 'phoenix':
        #     return Phoenix()
        # case 'example':
        #     return StrategyExample()
        # case 'time_based':
        #     return StrategyTimeBased()
        # case 'test_functions':
        #     return Test_functions()
        # case 'turnaround_tuesdays':
        #     return TurnaroundTuesdays()
        # case 'turnaround_tuesdaysv2':
        #     return TurnaroundTuesdaysV2()
        # case 'long_leverage':
        #     return StrategyLongLeverage()
        # case 'turnaround_daybreak':
        #     return TurnaroundDaybreak()
        # case 'turnaround_daybreakv2':
        #     return TurnaroundDaybreakV2()
        # case 'twinbreak':
        #     return TwinBreak()
        # case 'turnaround_daybreak_fix':
        #     return TurnaroundDaybreakFix()
        # case 'twinbreak_legacy':
        #     return TwinBreakLegacy()
        # case 'turnaround_shortbreak':
        #     return TurnaroundShortbreak()
        # case 'turnaround_daybreak_with_stop_loss':
        #     return TurnaroundStopLoss()
        # case 'turnaround_onlyshorts':
        #     return TurnaroundOnlyshorts()
        # case 'c_lab':
        #     return C_Lab()
        # case 'chadaybreak':
        #     return Chadaybreak()
        # case 'cha_yfin':
        #     return ChameleonNoPrint()
        # case 'c_lab_2':
        #     return C_Lab_2()
        # case 'evolved':
        #     return Evolved()
        case 'chameleon':
            return Chameleon()
        # case 'day':
        #     return StrategyDay()
        # case 'chameleon_v2':
        #     return ChameleonV2()
        # case 'ma':
        #     return MA()
        # case 'ibf':
        #     return IBF()
        # case 'ibf_bt':
        #     return IBF_BT()
        case 'hyper_bf':
            return HyperBF()
        case 'hbf_live':
            return HyperBF_Live()
        case 'hbf_lab':
            return HyperBF_Lab()
        case 'candlestick_test':
            return CandleStick_Test()
        case 'golden_bf':
            return GoldenBF()
        case 'oroboros':
            return Orobros()
        case 'hbf_hedged':
            return HyperBF_Hedged()
        case 'gbf_live':
            return GoldenBF_Live()
        case 'gbf_old':
            return GoldenBF_Old()
        case 'inverse_gbf':
            return Inverse_GBF()
        case _:
            raise ValueError(f"'{strategy_name}' is not a valid strategy name.")