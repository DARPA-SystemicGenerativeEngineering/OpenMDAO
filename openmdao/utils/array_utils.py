"""
Utils for dealing with arrays.
"""
from __future__ import print_function, division

import sys
import six
from six.moves import range

import numpy as np


def evenly_distrib_idxs(num_divisions, arr_size):
    """
    Return evenly distributed entries for the given array size.

    Given a number of divisions and the size of an array, chop the array up
    into pieces according to number of divisions, keeping the distribution
    of entries as even as possible.

    Parameters
    ----------
    num_divisions : int
        Number of parts to divide the array into.
    arr_size : int
        Number of entries in the array.

    Returns
    -------
    tuple
        a tuple of (sizes, offsets), where sizes and offsets contain values for all
        divisions.
    """
    base = arr_size // num_divisions
    leftover = arr_size % num_divisions
    sizes = np.full(num_divisions, base, dtype=int)

    # evenly distribute the remainder across size-leftover procs,
    # instead of giving the whole remainder to one proc
    sizes[:leftover] += 1

    offsets = np.zeros(num_divisions, dtype=int)
    offsets[1:] = np.cumsum(sizes)[:-1]

    return sizes, offsets


def take_nth(rank, size, seq):
    """
    Iterate returning every nth value.

    Return an iterator over the sequence that returns every
    nth element of seq based on the given rank within a group of
    the given size.  For example, if size = 2, a rank of 0 returns
    even indexed elements and a rank of 1 returns odd indexed elements.

    Parameters
    ----------
    rank : int
        MPI rank of this process.
    size : int
        Size of the array we're taking nth entries from.
    seq : iter
        Iterator containing the values being returned.
    """
    assert(rank < size)
    it = iter(seq)
    while True:
        for proc in range(size):
            if rank == proc:
                try:
                    yield six.next(it)
                except StopIteration:
                    return
            else:
                try:
                    six.next(it)
                except StopIteration:
                    return


def convert_neg(arr, dim):
    """
    Convert any negative indices into their positive equivalent.

    Parameters
    ----------
    arr : ndarray
        Array having negative indices converted.
    dim : int
        Dimension of the array.

    Returns
    -------
    ndarray
        The converted array.
    """
    arr[arr < 0] += dim
    return arr


def array_viz(arr, prob=None, of=None, wrt=None, stream=sys.stdout):
    """
    Display the structure of a boolean array in a compact form.

    If prob, of, and wrt are supplied, print the name of the response alongside
    each row and print the names of the design vars, aligned with each column, at
    the bottom.

    Parameters
    ----------
    arr : ndarray
        Array being visualized.
    prob : Problem or None
        Problem object.
    of : list of str or None
        Names of response variables used in derivative calculation.
    wrt : list of str or None
        Names of design variables used in derivative calculation.
    stream : file-like
        Stream where output will be written.
    """
    if len(arr.shape) != 2:
        raise RuntimeError("array_viz only works for 2d arrays.")

    if prob is not None:
        if of is None:
            of = prob.driver._get_ordered_nl_responses()
        if wrt is None:
            wrt = list(prob.driver._designvars)

    if prob is None or of is None or wrt is None:
        for r in range(arr.shape[0]):
            for c in range(arr.shape[1]):
                if arr[r, c]:
                    stream.write('x')
                else:
                    stream.write('.')
            stream.write(' %d\n' % r)
    else:

        row = 0
        for res in of:
            for r in range(row, row + prob.driver._responses[res]['size']):
                col = 0
                for dv in wrt:
                    for c in range(col, col + prob.driver._designvars[dv]['size']):
                        if arr[r, c]:
                            stream.write('x')
                        else:
                            stream.write('.')
                    col = c + 1
                stream.write(' %d  %s\n' % (r, res))
            row = r + 1

        start = 0
        for name in wrt:
            tab = ' ' * start
            stream.write('%s|%s\n' % (tab, name))
            start += prob.driver._designvars[name]['size']


def array_connection_compatible(shape1, shape2):
    """
    Return True if the two arrays shapes are compatible.

    Array shapes are compatible if the underlying data has the same size and is
    stored in the same contiguous order for the two shapes.

    Parameters
    ----------
    shape1 : tuple of int
        Shape of the first array.
    shape2 : tuple of int
        Shape of the second array.

    Returns
    -------
    bool
        True if the two shapes are compatible for connection, else False.
    """
    ashape1 = np.asarray(shape1, dtype=int)
    ashape2 = np.asarray(shape2, dtype=int)

    size1 = np.prod(ashape1)
    size2 = np.prod(ashape2)

    # Shapes are not connection-compatible if size is different
    if size1 != size2:
        return False

    nz1 = np.where(ashape1 > 1)[0]
    nz2 = np.where(ashape2 > 1)[0]

    if len(nz1) > 0:
        fundamental_shape1 = ashape1[np.min(nz1): np.max(nz1) + 1]
    else:
        fundamental_shape1 = np.ones((1,))

    if len(nz2) > 0:
        fundamental_shape2 = ashape2[np.min(nz2): np.max(nz2) + 1]
    else:
        fundamental_shape2 = np.ones((1,))

    return np.all(fundamental_shape1 == fundamental_shape2)


def tile_sparse_jac(data, rows, cols, nrow, ncol, num_nodes):
    """
    Assemble arrays necessary to define a COO sparse jacobian for a vectorized component.

    These arrays can also be passed to csc_matrix or csr_matrix to create CSC and CSR sparse
    matrices.

    Parameters
    ----------
    data : ndarray
        Array of values
    rows : index array
        Array of row indices.
    cols : index array
        Array of column indices.
    nrow : int
        Number of rows in sub jacobian.
    ncol : int
        Number of columns in sub jacobian.
    num_nodes : int
        Number of vectorized copies to tile.

    Returns
    -------
    ndarray, ndarray, ndarray
        Arrays to define a COO sparse jacobian of size num_nodes*nrow by num_nodes*ncol
    """
    nnz = len(rows)

    if np.isscalar(data):
        data = data * np.ones(nnz)

    if not np.isscalar(nrow):
        nrow = np.prod(nrow)

    if not np.isscalar(ncol):
        ncol = np.prod(ncol)

    repeat_arr = np.repeat(np.arange(num_nodes), nnz)

    data = np.tile(data, num_nodes)
    rows = np.tile(rows, num_nodes) + repeat_arr * nrow
    cols = np.tile(cols, num_nodes) + repeat_arr * ncol

    return data, rows, cols


def _global2local_offsets(global_offsets):
    """
    Given existing global offsets, return a copy with offsets localized to each process.

    Parameters
    ----------
    global_offsets : dict
        Arrays of global offsets keyed by vec_name and deriv direction.

    Returns
    -------
    dict
        Arrays of local offsets keyed by vec_name and deriv direction.
    """
    offsets = {}
    for vec_name in global_offsets:
        offsets[vec_name] = off_vn = {}
        for type_ in global_offsets[vec_name]:
            goff = global_offsets[vec_name][type_]
            off_vn[type_] = goff.copy()
            if goff[0].size > 0:
                # adjust offsets to be local in each process
                off_vn[type_] -= off_vn[type_][:, 0].reshape((goff.shape[0], 1))

    return offsets


def local_index_iter(sizes):
    """
    Generate local variable indices given an array of variable sizes.

    Parameters
    ----------
    sizes : ndarray of int
        Array of variable sizes.

    Yields
    ------
    int
        local intra-variable indices.
    """
    for size in sizes:
        for i in range(size):
            yield i


def var_name_idx_iter(names, sizes):
    """
    Generate variable names that will map to overall array index.

    Parameters
    ----------
    names : iter of str
        Iterator over variable names corresponding to the given sizes.
    sizes : ndarray of int
        Array of variable sizes.

    Yields
    ------
    str
        Variable name. Each name will be yielded a number of times equal to the variable size.
    """
    for name, size in zip(names, sizes):
        for i in range(size):
            yield name


def sub2full_indices(all_names, matching_names, sizes, idx_map=()):
    """
    Return the given indices converted into indices into the full vector.

    This routine is used to compute how column indices computed during coloring of a subset
    of the jacobian map to column indices corresponding to the full jacobian.

    Parameters
    ----------
    all_names : ordered iter of str
        An ordered list of variable names containing all variables of the appropriate type.
    matching_names : set of str
        Subset of all_names that make up the reduced index set.
    sizes : ndarray of int
        Array of variable sizes.
    idx_map : dict
        Mapping of var name to some subset of its full indices.

    Returns
    -------
    ndarray
        Full array indices that map to the provided subset of variables.
    """
    global_idxs = []
    start = end = 0
    for name, size in zip(all_names, sizes):
        end += size
        if size > 0 and (matching_names is None or name in matching_names):
            if name in idx_map:
                global_idxs.append(np.arange(start, end)[idx_map[name]])
            else:
                global_idxs.append(np.arange(start, end))
        start = end

    if global_idxs:
        return np.hstack(global_idxs)
    else:
        return None


def get_input_idx_split(full_idxs, inputs, outputs, is_implicit):
    """
    Split an array of indices into vec outs + ins into two arrays of indices into outs and ins.

    Parameters
    ----------
    full_idxs : ndarray
        Indices into the full array (which could be outs + ins or just ins)
    inputs : Vector
        Inputs vector.
    outputs : Vector
        Outputs vector.
    is_implicit : bool
        If True, current system is implicit and full idxs are into the full outs + ins vector.

    Returns
    -------
    list of tuples
        Each tuple is of the form (array, idxs).
    """
    assert len(full_idxs) > 0, "Empty index array passed to get_input_idx_split."
    if is_implicit:
        full_size = inputs._data.size
        out_size = outputs._data.size
        full_size += out_size
        out_idxs = full_idxs[full_idxs < out_size]
        in_idxs = full_idxs[full_idxs >= out_size]
        if out_idxs.size > 0 and in_idxs.size > 0:
            return [(inputs, in_idxs - out_size), (outputs, out_idxs)]
        elif in_idxs.size > 0:
            return [(inputs, in_idxs - out_size)]
        else:  # out_idxs.size > 0
            return [(outputs, out_idxs)]
    else:
        return [(inputs, full_idxs)]


def get_index_array_maps(names, sizes):
    """
    Given names and sizes, return mappings of names and local indices to array index.

    Parameters
    ----------
    names : iter of str
        Iterator over the names.  (Must be ordered.)
    sizes : ndarray of int
        Sizes of variables specified in names.

    Returns
    -------
    list
        list of length sum(sizes) containing corresponding var name in each entry.
    ndarray
        Array of length sum(sizes) with var local index in each entry.
    """
    tot_size = np.sum(sizes)
    name_list = [None] * tot_size
    loc_idxs = np.empty(tot_size, dtype=numpy.uint32)

    start = end = 0
    for name, size in zip(names, sizes):
        end += size
        if size > 0:
            name_list[start:end] = name
            loc_idxs[start:end] = np.arange(size, dtype=uint32)
        start = end

    return name_list, loc_idxs


def get_local_offset_map(names, sizes):
    """
    Return a mapping of var name to local offset.

    Parameters
    ----------
    names : list of str
        Variable names.
    sizes : ndarray of int
        Local variable sizes.

    Returns
    -------
    dict
        Mapping of var name to local offset.
    """
    offsets = {}
    start = end = 0
    for name, size in zip(names, sizes):
        end += size
        if end != start:
            offsets[name] = start
        start = end
    return offsets


def update_sizes(names, sizes, index_map):
    """
    Return a sizes array, with possibly some sizes reduced to agree with index_map.

    Parameters
    ----------
    names : list of str
        Names of variables associated with sizes.
    sizes : ndarray
        Array of sizes of each variable.
    index_map : dict
        Mapping of variable name to some subset of indices.

    Returns
    -------
    ndarray
        Sizes of variables after reducing some due to index_map.
    """
    if index_map:
        sizes = sizes.copy()
        for i, (name, size) in enumerate(zip(names, sizes)):
            if size > 0 and name in index_map:
                sizes[i] = len(index_map[name])

    return sizes
