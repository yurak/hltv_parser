from normaliser import Normaliser
from maps_filter import MapsFilter
from analyser import Analyser
Normaliser('../hltv_attributes_selenium_top20_competetive_maps.csv', 'top_20_normalized_competetive_maps.csv').call()
MapsFilter().call()
Analyser().call()
