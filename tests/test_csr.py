# Copyright 2022 NVIDIA Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import cunumeric as np
import pytest
from sparse import csr_array, runtime
import scipy.sparse as scpy
from legate.core.solver import Partitioner
import os

import sparse.io as legate_io
import scipy.io as sci_io
import numpy

from common import test_mtx_files


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_from_dense(filename):
    l = csr_array(legate_io.mmread(filename).todense())
    s = scpy.csr_array(sci_io.mmread(filename).todense())
    assert np.array_equal(l.todense(), s.todense())


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_to_coo(filename):
    l = legate_io.mmread(filename).tocsr()
    assert np.array_equal(l.todense(), l.tocoo().todense())


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_from_scipy_csr(filename):
    s = scpy.csr_array(sci_io.mmread(filename).todense())
    l = csr_array(s)
    assert np.array_equal(l.todense(), s.todense())


@pytest.mark.parametrize("filename", test_mtx_files)
@pytest.mark.parametrize("copy", [False])
def test_csr_conj(filename, copy):
    l = legate_io.mmread(filename).tocsr().conj(copy=copy)
    s = sci_io.mmread(filename).tocsr().conj(copy=copy)
    assert np.array_equal(l.todense(), s.todense())


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_dot(filename):
    # Test vectors and n-1 matrices.
    l = legate_io.mmread(filename).tocsr()
    s = sci_io.mmread(filename).tocsr()
    vec = np.random.random((l.shape[0]))
    assert np.allclose(l @ vec, s @ vec)
    assert np.allclose(l.dot(vec), s.dot(vec))
    result_l = np.zeros((l.shape[0]))
    l.dot(vec, out=result_l)
    assert np.allclose(result_l, s.dot(vec))
    vec = np.random.random((l.shape[0], 1))
    assert np.allclose(l @ vec, s @ vec)
    assert np.allclose(l.dot(vec), s.dot(vec))
    result_l = np.zeros((l.shape[0], 1))
    l.dot(vec, out=result_l)
    assert np.allclose(result_l, s.dot(vec))


@pytest.mark.parametrize("filename", test_mtx_files)
def test_balance_row_partitions(filename):
    # Test vectors and n-1 matrices.
    l = legate_io.mmread(filename).tocsr()
    l.balance()
    s = sci_io.mmread(filename).tocsr()
    vec = np.random.random((l.shape[0]))
    assert np.allclose(l @ vec, s @ vec)
    assert np.allclose(l.dot(vec), s.dot(vec))
    vec = np.random.random((l.shape[0], 1))
    assert np.allclose(l @ vec, s @ vec)
    assert np.allclose(l.dot(vec), s.dot(vec))


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_spmm(filename):
    l = legate_io.mmread(filename)
    s = sci_io.mmread(filename)
    res_legate = l.tocsr() @ l.todense()
    res_sci = s.tocsr() @ s.todense()
    assert np.allclose(res_legate, res_sci)
    result = np.zeros(l.shape)
    l.tocsr().dot(l.todense(), out=result)
    assert np.allclose(res_legate, res_sci)


@pytest.mark.parametrize("filename", test_mtx_files)
@pytest.mark.parametrize("idim", [2, 4, 8, 16])
def test_csr_spmm_rmatmul(filename, idim):
    l = legate_io.mmread(filename).tocsr()
    x = np.ones((idim, l.shape[1]))
    s = sci_io.mmread(filename).tocsr()
    # TODO (rohany): Until we have the dispatch with cunumeric
    #  then we can stop explicitly calling __rmatmul__. We also
    #  can't even do it against the scipy matrix because it doesn't
    #  have the overload either.
    assert np.allclose(l.__rmatmul__(x), numpy.array(x) @ s)


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_csr_csr_spgemm(filename):
    l = legate_io.mmread(filename)
    s = sci_io.mmread(filename).tocsr()
    res_legate = l.tocsr() @ l.tocsr()
    res_sci = s @ s
    assert np.allclose(res_legate.todense(), res_sci.todense())


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_csr_csc_spgemm(filename):
    l = legate_io.mmread(filename)
    s = sci_io.mmread(filename)
    res_legate = l.tocsr() @ l.tocsc()
    res_sci = s.tocsr() @ s.tocsc()
    assert np.allclose(res_legate.todense(), res_sci.todense())


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_transpose(filename):
    l = legate_io.mmread(filename).tocsr().T
    s = sci_io.mmread(filename).tocsr().T
    assert np.array_equal(l.todense(), numpy.ascontiguousarray(s.todense()))


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_todense(filename):
    l = legate_io.mmread(filename).tocsr()
    s = sci_io.mmread(filename).tocsr()
    assert np.array_equal(l.todense(), s.todense())


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_elemwise_mul(filename):
    l = legate_io.mmread(filename)
    s = sci_io.mmread(filename)
    res_legate = l.tocsr() * csr_array(np.roll(l.todense(), 1))
    res_scipy = s.tocsr() * scpy.csr_array(np.roll(np.array(s.todense()), 1))
    assert np.allclose(res_legate.todense(), res_scipy.todense())


@pytest.mark.parametrize("filename", test_mtx_files)
@pytest.mark.parametrize("kdim", [2, 4, 8, 16])
def test_csr_sddmm(filename, kdim):
    l = legate_io.mmread(filename).tocsr()
    s = sci_io.mmread(filename).tocsr()
    C = np.random.random((l.shape[0], kdim))
    D = np.random.random((kdim, l.shape[1]))
    res_legate = l.sddmm(C, D)
    # This version of scipy still thinks that * is matrix multiplication instead
    # of element-wise multiplication, so we have to use multiply().
    res_scipy = s.multiply(numpy.array(C @ D))
    assert np.allclose(res_legate.todense(), res_scipy.todense())


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_dense_elemwise_mul(filename):
    l = legate_io.mmread(filename)
    s = sci_io.mmread(filename)
    c = np.random.random(l.shape)
    res_legate = l.tocsr() * c
    # The version of scipy that I have locally still thinks * is matmul.
    res_scipy = s.tocsr().multiply(numpy.array(c))
    assert np.allclose(res_legate.todense(), res_scipy.todense())


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_elemwise_add(filename):
    l = legate_io.mmread(filename)
    s = sci_io.mmread(filename)
    res_legate = l.tocsr() + csr_array(np.roll(l.todense(), 1))
    res_scipy = s.tocsr() + scpy.csr_array(np.roll(s.toarray(), 1))
    assert np.allclose(res_legate.todense(), res_scipy.todense())


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_to_scipy_csr(filename):
    l = legate_io.mmread(filename).tocsr()
    s = sci_io.mmread(filename).tocsr()
    assert np.array_equal(l.to_scipy_sparse_csr().todense(), s.todense())


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_mul_scalar(filename):
    l = legate_io.mmread(filename).tocsr()
    s = sci_io.mmread(filename).tocsr()
    res_legate = l * 3.0
    res_sci = s * 3.0
    assert np.allclose(res_legate.todense(), res_sci.todense())


@pytest.mark.parametrize("filename", test_mtx_files)
def test_csr_subtract(filename):
    l = legate_io.mmread(filename)
    s = sci_io.mmread(filename)
    res_legate = l.tocsr() - csr_array(np.roll(l.todense(), 1))
    res_scipy = s.tocsr() - scpy.csr_array(np.roll(s.toarray(), 1))
    assert np.allclose(res_legate.todense(), res_scipy.todense())


# The goal of this test is to ensure that when we balance the rows
# of CSR matrix, we actually use that partition in operations. We'll
# do this by by being really hacky. We'll increase the runtime's window
# size, and inspecting what would happen if the solver partitions the
# operation within the window.
def test_csr_rmatmul_balanced():
    sparse_rt = runtime.runtime
    rt = sparse_rt.legate_runtime
    if sparse_rt.num_procs == 1:
        pytest.skip("Must run with multiple processors.")
    if "LEGATE_TEST" not in os.environ:
        pytest.skip("Partitioning must be forced with LEGATE_TEST=1")
    filename = "testdata/test.mtx"
    l = legate_io.mmread(filename).tocsr()
    s = sci_io.mmread(filename).tocsr()
    l.balance()
    # idim must be small enough so that the solver doesn't think that
    # re-partitioning x or the output will cause more data movement.
    idim = 2
    x = np.ones((idim, l.shape[1]))
    rt._window_size = 3
    rt.flush_scheduling_window()
    res = l.__rmatmul__(x)
    # We expect to find the cunumeric zero task and the SpMM task.
    assert len(rt._outstanding_ops) == 2
    partitioner = Partitioner([rt._outstanding_ops[1]], must_be_single=False)
    strat = partitioner.partition_stores()
    assert "by_domain" in str(strat)
    rt._window_size = 1
    rt.flush_scheduling_window()
    # Ensure that the answer is correct.
    assert np.allclose(res, numpy.array(x) @ s)


def test_csr_sddmm_balanced():
    sparse_rt = runtime.runtime
    rt = sparse_rt.legate_runtime
    if sparse_rt.num_procs == 1:
        pytest.skip("Must run with multiple processors.")
    if "LEGATE_TEST" not in os.environ:
        pytest.skip("Partitioning must be forced with LEGATE_TEST=1")
    filename = "testdata/test.mtx"
    l = legate_io.mmread(filename).tocsr()
    s = sci_io.mmread(filename).tocsr()
    l.balance()
    # idim must be small enough so that the solver doesn't think that
    # re-partitioning x or the output will cause more data movement.
    kdim = 2
    C = np.random.random((l.shape[0], kdim))
    D = np.random.random((kdim, l.shape[1]))
    rt._window_size = 2
    rt.flush_scheduling_window()
    res = l.sddmm(C, D)
    assert len(rt._outstanding_ops) == 1
    partitioner = Partitioner([rt._outstanding_ops[0]], must_be_single=False)
    strat = partitioner.partition_stores()
    assert "by_domain" in str(strat)
    rt._window_size = 1
    rt.flush_scheduling_window()
    # Ensure that the answer is correct.
    assert np.allclose(res.todense(), s.multiply(numpy.array(C @ D)).todense())


if __name__ == "__main__":
    import sys
    sys.exit(pytest.main(sys.argv))
