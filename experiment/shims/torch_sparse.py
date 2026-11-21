r"""Minimal stand-in for the parts of ``torch_sparse`` used by the official
baseline scripts in ``baselines/`` (SparseTensor + matmul), implemented on top
of ``torch.sparse``.

The model actually used to train the released synthetic graphs is ``GCNE``
(PyG ``GCNConv`` with edge weights), so the ``SparseTensor`` built by the
loaders is never touched during the forward pass -- this shim only has to be
constructible.
"""

from __future__ import annotations

import torch


class SparseTensor:
    def __init__(self, row=None, col=None, value=None, sparse_sizes=None):
        index = torch.stack([row.long(), col.long()], dim=0)
        self._t = torch.sparse_coo_tensor(index, value, sparse_sizes).coalesce()
        self.sparse_sizes = sparse_sizes

    def to(self, *args, **kwargs):
        return self

    def size(self):
        return self._t.shape

    def _indices(self):
        return self._t._indices()

    def _values(self):
        return self._t._values()

    def __repr__(self) -> str:  # pragma: no cover
        return f"SparseTensor(shape={self.size()}, nnz={self._t._nnz()})"


def matmul(sparse, dense):
    return torch.sparse.mm(sparse._t, dense)
