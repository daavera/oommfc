import re
import os
import glob
import shutil
import oommfc as oc
import ubermagtable as ut
import discretisedfield as df
import micromagneticmodel as mm


def oxs_class(term):
    mif = getattr(oc.scripts.energies, f'{term.name}_script')(term)
    return re.search(r'Oxs_([\w_]+)', mif).group(1)


def schedule_script(func):
    if func.__name__ == 'energy':
        return ''  # Datatable with energies is saved by default.
    elif func.__name__ == 'effective_field':
        if isinstance(func.__self__, mm.Energy):
            output = 'Oxs_RungeKuttaEvolve:evolver:Total field'
        else:
            output = f'Oxs_{oxs_class(func.__self__)}::Field'
    elif func.__name__ == 'density':
        if isinstance(func.__self__, mm.Energy):
            output = 'Oxs_RungeKuttaEvolve:evolver:Total energy density'
        else:
            output = f'Oxs_{oxs_class(func.__self__)}::Energy density'

    return 'Schedule \"{}\" archive Step 1\n'.format(output)


def compute(func, system):
    """Computes a particular value of an energy term or energy container
    (``energy``, ``density``, or ``effective_field``).

    Parameters
    ----------
    func : callable

        A property of an energy term or an energy container.

    system : micromagneticmodel.System

        Micromagnetic system for which the property is calculated.

    Returns
    -------
    numbers.Real, discretisedfield.Field

        Resulting value.

    Examples
    --------
    1. Computing values of energy terms.

    >>> import micromagneticmodel as mm
    >>> import oommfc as oc
    ...
    >>> system = mm.examples.macrospin()
    >>> oc.compute(system.energy.zeeman.energy, system)
    20...Running OOMMF...
    -8.8...e-22
    >>> oc.compute(system.energy.effective_field, system)
    20...Running OOMMF...
    Field(...)
    >>> oc.compute(system.energy.density, system)
    20...Running OOMMF...
    Field(...)

    """
    td = oc.TimeDriver(total_iteration_limit=1)
    td.drive(system, t=1e-25, n=1, save=True, overwrite=True,
             compute=schedule_script(func))

    if func.__name__ == 'energy':
        extension = '*.odt'
    elif func.__name__ == 'effective_field':
        extension = '*.ohf'
    elif func.__name__ == 'density':
        extension = '*.oef'
    else:
        msg = f'Computing the value of {func} is not supported.'
        raise ValueError(msg)

    dirname = os.path.join(system.name, f'compute-{system.drive_number}')
    output_file = max(glob.iglob(os.path.join(dirname, extension)),
                      key=os.path.getctime)

    if func.__name__ == 'energy':
        table = ut.read(output_file, rename=False)
        if isinstance(func.__self__, mm.Energy):
            output = table['RungeKuttaEvolve:evolver:Total energy'][0]
        else:
            output = table[f'{oxs_class(func.__self__)}::Energy'][0]
    else:
        output = df.Field.fromfile(output_file)

    # Delete "compute" directory after the data is extracted.
    shutil.rmtree(dirname)

    return output