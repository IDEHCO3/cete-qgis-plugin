  # coding: utf-8
 
 # Codigo de conversao de eWkb para wkb retirado do plugin QuickWKT para Qgis
 # https://github.com/elpaso/quickwkt/blob/master/QuickWKT.py#L144
 
import binascii
 
def hexToWkb(wkb):
	SRID_FLAG = 0x20000000
	geomType = int("0x" + decodeBinary(wkb[2:10]), 0)
	
	if geomType & SRID_FLAG:
		srid = int("0x" + decodeBinary(wkb[10:18]), 0)

		# String the srid from the wkb string
		wkb = wkb[:2] + encodeBinary(geomType ^ SRID_FLAG) + wkb[18:]

	return wkb
		
		
def decodeBinary(wkb):
	"""Decode the binary wkb and return as a hex string"""
	value = binascii.a2b_hex(wkb)
	value = value[::-1]
	value = binascii.b2a_hex(value)
	return value.decode("UTF-8")

	
def encodeBinary(value):
	wkb = binascii.a2b_hex("%08x" % value)
	wkb = wkb[::-1]
	wkb = binascii.b2a_hex(wkb)
	return wkb.decode("UTF-8")