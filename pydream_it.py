import sys
import importlib

def parse_directive(directive, priors, no_sample):
    words = directive.split()
    if words[1] == 'prior':
        priors[words[2]] = words[3]
    elif words[1] == 'no-sample':
        no_sample.append(words[2])
    return

def prune_no_samples(parameters, no_sample):
    parameters = [parameter for parameter in parameters if parameter[0] not in no_sample]
    return parameters

def write_norm_param(p_name, p_val):
    line = "sp_{} = SampledParam(norm, loc=np.log10({}), scale=2.0)\n".format(p_name, p_val)
    return line

def write_uniform_param(p_name, p_val):
    line = "sp_{} = SampledParam(uniform, loc=np.log10({})-1.0, scale=2.0)\n".format(p_name, p_val)
    return line

model_file = sys.argv[1]
print("Using model from file: {}".format(model_file))
default_prior_shape = 'norm'
print("The default prior shape is: {}".format(default_prior_shape))
use_GR_converge = False
#print(model_file)
model_module_name = model_file[:-3]
#print(model_module_name)
model_module = importlib.import_module(model_module_name)
model = getattr(model_module, 'model')
#print(model)
priors = dict()
no_sample = list()
#Read the file and parse any #PYDREAM_IT directives
print("Parsing the model for any #PYDREAM_IT directives...")
with open(model_file, 'r') as file_obj:
    for line in file_obj:
        words = line.split()
        if len(words) > 1:
            if words[0] == '#PYDREAM_IT':
                parse_directive(line, priors, no_sample)

#now we need to extract a list of kinetic parameters
parameters = list()
print("Inspecting the model and pulling out kinetic parameters...")
for rule in model.rules:
    rule_keys = rule.__dict__.keys()
    #print(rule_keys)
    if 'rate_forward' in rule_keys:
        param = rule.__dict__['rate_forward']
        #print(param)
        parameters.append([param.name, param.value,'f'])
    if 'rate_reverse' in rule_keys:
        param = rule.__dict__['rate_reverse']
        #print(param)
        if param is not None:
            parameters.append([param.name, param.value, 'r'])
#print(parameters)
#print(no_sample)
parameters = prune_no_samples(parameters, no_sample)
#print(parameters)
print("Found the following kinetic parameters:")
print("{}".format(parameters))
#default the priors to norm - i.e. normal distributions
for parameter in parameters:
    name = parameter[0]
    if name not in priors.keys():
        priors[name] = default_prior_shape

out_file = open("run_pydream_"+model_file, 'w')
print("Writing to PyDREAM run script: run_pydream_{}".format(model_file))
out_file.write("from pydream.core import run_dream\n")
out_file.write("from pysb.integrate import Solver\n")
out_file.write("import numpy as np\n")
out_file.write("from pydream.parameters import SampledParam\n")
#out_file.write("from pydream.convergence import Gelman_Rubin")
out_file.write("from scipy.stats import norm,uniform\n")
#out_file.write("import inspect\n")
#out_file.write("import os.path\n")
out_file.write("from "+model_module_name+" import model\n")
out_file.write("\n")
out_file.write("# DREAM Settings\n")
out_file.write("# Number of chains - should be at least 3.\n")
out_file.write("nchains = 5\n")

out_file.write("# Number of iterations\n")
out_file.write("niterations = 50000\n")
out_file.write("\n")
out_file.write("#Initialize PySB solver object for running simulations.  Simulation timespan should match experimental data.\n")
out_file.write("tspan = np.linspace(0,10, num=100)\n")
out_file.write("solver = Solver(model, tspan)\n")
out_file.write("solver.run()\n")
out_file.write("\n")
out_file.write("# USER must add commands to import/load any experimental data for use in the likelihood function!\n")
out_file.write("# USER must define a likelihood function!\n")
out_file.write("def likelihood(param_vector):\n")
out_file.write("    pass\n")
out_file.write("\n")
#write the sampled params lines
out_file.write("sampled_params_list = list()\n")
for parameter in parameters:
    name = parameter[0]
    value = parameter[1]
    prior_shape = priors[name]
    print("Will sample parameter {} with {} prior around {}".format(name, prior_shape, value))
    if prior_shape == 'uniform':
        line = write_uniform_param(name, value)
        ps_name = line.split()[0]
        out_file.write(line)
        out_file.write("sampled_params_list.append({})\n".format(ps_name))
    else:
        line = write_norm_param(name, value)
        ps_name = line.split()[0]
        out_file.write(line)
        out_file.write("sampled_params_list.append({})\n".format(ps_name))

if use_GR_converge:
    pass
else:
    out_file.write("sampled_params, log_ps = run_dream(parameters=sampled_params_list, likelihood=likelihood, niterations=niterations, nchains=nchains, multitry=False, gamma_levels=4, adapt_gamma=True, history_thin=1, model_name=\'dreamzs_5chain\', verbose=True)\n")
    out_file.write("total_iterations = niterations\n")
    out_file.write("# Save sampling output (sampled parameter values and their corresponding logps).\n")
    out_file.write("for chain in range(len(sampled_params)):\n")
    out_file.write("    np.save(\'dreamzs_5chain_sampled_params_chain_\' + str(chain)+\'_\'+str(total_iterations), sampled_params[chain])\n")
    out_file.write("    np.save(\'dreamzs_5chain_logps_chain_\' + str(chain)+\'_\'+str(total_iterations), log_ps[chain])\n")

out_file.close()
print("pydream_it is complete!")
print("END OF LINE.")
