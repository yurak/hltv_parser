from normaliser import Normaliser
from maps_filter import MapsFilter
from analyser import Analyser
Normaliser('../hltv_attributes_selenium_top20_ext.csv', 'top_20_normalized.csv').call()
MapsFilter().call()
Analyser().call()
