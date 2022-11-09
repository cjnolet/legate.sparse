/* Copyright 2022 NVIDIA Corporation
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 *
 */

#pragma once

#include "sparse.h"
#include "sparse_c.h"
#include "legate.h"

namespace sparse {

struct COOToDenseArgs {
  const legate::Store& result;
  const legate::Store& rows;
  const legate::Store& cols;
  const legate::Store& vals;
};

class COOToDense : public SparseTask<COOToDense> {
 public:
  static const int TASK_ID = LEGATE_SPARSE_COO_TO_DENSE;
  static void cpu_variant(legate::TaskContext& ctx);
};

}  // namespace sparse
