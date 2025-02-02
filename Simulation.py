
import time
import signal
from pyModbusTCP.client import ModbusClient
from pyModbusTCP.utils import encode_ieee, decode_ieee, long_list_to_word, word_list_to_long

from fmpy import *
from fmpy.fmi2 import FMU2Slave

import shutil

from parse import parse

def read_float(client, address, number=1):
    """Read float(s) with read holding registers."""
    reg_l = client.read_holding_registers(address, number * 2)
    assert(reg_l)
    return [decode_ieee(f) for f in word_list_to_long(reg_l)]
    
def write_float(client, address, floats_list):
    """Write float(s) with write multiple registers."""
    b32_l = [encode_ieee(f) for f in floats_list]
    b16_l = long_list_to_word(b32_l)
    return client.write_multiple_registers(address, b16_l)

def parse_plc_vars(st_filename):
	with open(st_filename) as file:
		plcvars = {}
		for line in file:
        		r = parse('{name} AT %{location:1.1}X{address0}.{address1} : BOOL;',line.strip())
        		if r: 
        			index = int(r['address0']) * 8 + int(r['address1'])
        			plcvars[r['name']] = { 'name': r['name'], 'index': index, 'type': 'BOOL' }
        			continue
        		r = parse('{name} AT %{location:1.1}{size:1.1}{address} : {type};',line.strip())
        		if r: 
        			index = int(r['address'])
        			if (r['location'] == 'M' and r['size'] == 'W'):
        				index = 1024 + index 
        			if (r['location'] == 'M' and r['size'] == 'D'):
        				index = 2048 + (index * 2)
        			if (r['location'] == 'M' and r['size'] == 'L'):
        				index = 4096 + (index * 4)
        			plcvars[r['name']] = { 'name': r['name'], 'index': index, 'type': r['type'] }
        			continue
		for p in plcvars:
			print('PLC {}'.format(plcvars[p]))
		return plcvars


def init_fmu(fmu_filename):

	dump(fmu_filename)

	model_description = read_model_description(fmu_filename)
	fmuvars = {}
	for variable in model_description.modelVariables:
		fmuvars[variable.name] = { 
			'name': variable.name, 
			'reference': variable.valueReference,
			'type': variable.type,
			'causality': variable.causality 
			}
	for f in fmuvars:
		print('FMU {}'.format(fmuvars[f]))

	unzipdir = extract(fmu_filename)

	return FMU2Slave(
		guid=model_description.guid,
		unzipDirectory=unzipdir,
		modelIdentifier=model_description.coSimulation.modelIdentifier,
		instanceName='instance1'), fmuvars


def init_modbus(hostname='localhost',port=502):
	client = ModbusClient(hostname,port=port)
	print(client)
	return client

def map_variables(plcvars,fmuvars):
	
	plc2fmu = []
	fmu2plc = []
	
	for p in plcvars:
		for f in fmuvars:
			if p == f.replace('.','_'):
				if fmuvars[f]['causality'] == 'input':
					plc2fmu.append((plcvars[p],fmuvars[f]))
					print('PLC {} -> FMU {}'.format(p,f))
				if fmuvars[f]['causality'] in ['output']: #,'local']:
					fmu2plc.append((fmuvars[f],plcvars[p]))
					print('FMU {} -> PLC {}'.format(f,p))

	return plc2fmu, fmu2plc

step_size = 1e-3
abort = False
never = -1.0

def run_cosimulation(modbus,plcvars,fmu,fmuvars,stop_time):

	plc2fmu, fmu2plc = map_variables(plcvars,fmuvars)
	
	t = 0.0

	while (t < stop_time or stop_time == never) and not abort:

		print('Elapsed simulation time: {:.4}s'.format(t),end='\r')

		for plcvar, fmuvar in plc2fmu:
			if plcvar['type'] == 'BOOL' and fmuvar['type'] == 'Boolean':
				fmu.setBoolean([fmuvar['reference']], modbus.read_coils(plcvar['index'],1))
			if plcvar['type'] in ['SINT','INT','DINT','LINT','USINT','UINT','UDINT','ULINT'] and fmuvar['type'] == 'Real':
				fmu.setReal([fmuvar['reference']], [float(modbus.read_holding_registers(plcvar['index'],1)[0])])
			if plcvar['type'] in ['REAL','LREAL'] and fmuvar['type'] == 'Real':
				fmu.setReal([fmuvar['reference']], [float(read_float(modbus,plcvar['index'],1)[0])])
			if plcvar['type'] in ['SINT','INT','DINT','LINT','USINT','UINT','UDINT','ULINT'] and fmuvar['type'] == 'Integer':
				fmu.setInteger([fmuvar['reference']], [int(modbus.read_holding_registers(plcvar['index'],1)[0])])
			if plcvar['type'] in ['REAL','LREAL'] and fmuvar['type'] == 'Integer':
				fmu.setInteger([fmuvar['reference']], [int(read_float(modbus,plcvar['index'],1)[0])])

		wct = time.time()
				
		fmu.doStep(currentCommunicationPoint=t, communicationStepSize=step_size)

		t += step_size

		for fmuvar, plcvar in fmu2plc:
			if fmuvar['type'] == "Boolean" and plcvar['type'] == 'BOOL':
				modbus.write_single_coil(plcvar['index'],int(fmu.getBoolean([fmuvar['reference']])[0]))
			if fmuvar['type'] == "Real" and plcvar['type'] in ['SINT','INT','DINT','LINT','USINT','UINT','UDINT','ULINT']:
				modbus.write_single_register(plcvar['index'],int(fmu.getReal([fmuvar['reference']])[0]))
			if fmuvar['type'] == "Real" and plcvar['type'] in ['REAL','LREAL']:
				write_float(modbus, plcvar['index'], [float(r) for r in fmu.getReal([fmuvar['reference']])])
			if fmuvar['type'] == "Integer" and plcvar['type'] in ['SINT','INT','DINT','LINT','USINT','UINT','UDINT','ULINT']:
				modbus.write_single_register(plcvar['index'],int(fmu.getInteger([fmuvar['reference']])[0]) & 0xffff)
			if fmuvar['type'] == "Integer" and plcvar['type'] in ['REAL','LREAL']:
				write_float(modbus, plcvar['index'], [float(r) for r in fmu.getInteger([fmuvar['reference']])])

		time.sleep(max((wct + step_size) - time.time(), 0))


def exit_signal(signum, frame):
	global abort
	print('Aborting...')
	abort = True

def run(fmu_filename, st_filename, stop_time):
	signal.signal(signal.SIGINT, exit_signal)
	signal.signal(signal.SIGTERM, exit_signal)

	plcvars = parse_plc_vars(st_filename)

	fmu, fmuvars = init_fmu(fmu_filename)
	fmu.instantiate()
	fmu.setupExperiment(startTime=0.0)
	fmu.enterInitializationMode()
	fmu.exitInitializationMode()

	modbus = init_modbus()

	run_cosimulation(modbus,plcvars,fmu,fmuvars,stop_time)

	fmu.terminate()
	fmu.freeInstance()
	shutil.rmtree(fmu.unzipDirectory, ignore_errors=True)


if __name__ == "__main__":
	if len(sys.argv) not in [3,4,5]:
		print('Usage: {} <FMU file> <ST file> [<step size>] [<duration>]'.format(sys.argv[0]))
		exit()
	fmu_filename = sys.argv[1]
	st_filename = sys.argv[2]
	if len(sys.argv) > 3:
		step_size = float(sys.argv[3])
	else:
		step_size = .01
	if len(sys.argv) > 4:
		stop_time = float(sys.argv[4])
	else:
		stop_time = never

	run(fmu_filename,st_filename,stop_time)


