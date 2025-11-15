/**
 * CUDA Kernels for Salary Analytics
 * GPU-accelerated computations for employee salary data
 *
 * Compile with: nvcc -ptx salary_kernels.cu -o salary_kernels.ptx
 */

#include <cuda_runtime.h>
#include <math.h>

/**
 * Kernel: Parallel Sum Reduction
 * Efficiently computes sum of salary array using shared memory
 */
extern "C" __global__
void salary_sum_kernel(const float* salaries, float* result, int n) {
    extern __shared__ float sdata[];

    unsigned int tid = threadIdx.x;
    unsigned int i = blockIdx.x * blockDim.x + threadIdx.x;

    // Load data into shared memory
    sdata[tid] = (i < n) ? salaries[i] : 0;
    __syncthreads();

    // Reduction in shared memory
    for (unsigned int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (tid < s) {
            sdata[tid] += sdata[tid + s];
        }
        __syncthreads();
    }

    // Write result for this block to global memory
    if (tid == 0) {
        atomicAdd(result, sdata[0]);
    }
}

/**
 * Kernel: Parallel Average Calculation
 * Computes average salary with Welford's online algorithm
 */
extern "C" __global__
void salary_average_kernel(const float* salaries, float* mean, int n) {
    extern __shared__ float sdata[];

    unsigned int tid = threadIdx.x;
    unsigned int i = blockIdx.x * blockDim.x + threadIdx.x;

    // Parallel sum
    sdata[tid] = (i < n) ? salaries[i] : 0;
    __syncthreads();

    for (unsigned int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (tid < s) {
            sdata[tid] += sdata[tid + s];
        }
        __syncthreads();
    }

    if (tid == 0) {
        atomicAdd(mean, sdata[0]);
    }
}

/**
 * Kernel: Parallel Min/Max Finding
 * Finds minimum and maximum salaries efficiently
 */
extern "C" __global__
void salary_min_max_kernel(const float* salaries, float* min_val, float* max_val, int n) {
    extern __shared__ float smin[];
    extern __shared__ float smax[];

    unsigned int tid = threadIdx.x;
    unsigned int i = blockIdx.x * blockDim.x + threadIdx.x;

    // Initialize shared memory
    smin[tid] = (i < n) ? salaries[i] : INFINITY;
    smax[tid] = (i < n) ? salaries[i] : -INFINITY;
    __syncthreads();

    // Reduction for min and max
    for (unsigned int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (tid < s) {
            smin[tid] = fminf(smin[tid], smin[tid + s]);
            smax[tid] = fmaxf(smax[tid], smax[tid + s]);
        }
        __syncthreads();
    }

    // Write results
    if (tid == 0) {
        atomicMin((int*)min_val, __float_as_int(smin[0]));
        atomicMax((int*)max_val, __float_as_int(smax[0]));
    }
}

/**
 * Kernel: Variance Calculation
 * Computes variance using two-pass algorithm
 */
extern "C" __global__
void salary_variance_kernel(const float* salaries, float mean, float* variance, int n) {
    extern __shared__ float sdata[];

    unsigned int tid = threadIdx.x;
    unsigned int i = blockIdx.x * blockDim.x + threadIdx.x;

    // Calculate squared differences
    float diff = (i < n) ? (salaries[i] - mean) : 0;
    sdata[tid] = diff * diff;
    __syncthreads();

    // Reduction
    for (unsigned int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (tid < s) {
            sdata[tid] += sdata[tid + s];
        }
        __syncthreads();
    }

    if (tid == 0) {
        atomicAdd(variance, sdata[0]);
    }
}

/**
 * Kernel: Parallel Percentile Calculation (Approximate)
 * Uses histogram-based approach for fast percentile estimation
 */
extern "C" __global__
void salary_histogram_kernel(
    const float* salaries,
    int* histogram,
    float min_val,
    float max_val,
    int num_bins,
    int n
) {
    unsigned int i = blockIdx.x * blockDim.x + threadIdx.x;

    if (i < n) {
        float salary = salaries[i];
        float range = max_val - min_val;
        int bin = (int)((salary - min_val) / range * (num_bins - 1));

        if (bin >= 0 && bin < num_bins) {
            atomicAdd(&histogram[bin], 1);
        }
    }
}

/**
 * Kernel: Department-wise Salary Aggregation
 * Groups salaries by department and computes statistics
 */
extern "C" __global__
void dept_salary_aggregate_kernel(
    const float* salaries,
    const int* dept_ids,
    float* dept_sums,
    int* dept_counts,
    int n,
    int num_depts
) {
    unsigned int i = blockIdx.x * blockDim.x + threadIdx.x;

    if (i < n) {
        int dept = dept_ids[i];
        if (dept >= 0 && dept < num_depts) {
            atomicAdd(&dept_sums[dept], salaries[i]);
            atomicAdd(&dept_counts[dept], 1);
        }
    }
}

/**
 * Kernel: Salary Growth Rate Calculation
 * Computes year-over-year growth rates
 */
extern "C" __global__
void salary_growth_kernel(
    const float* current_salaries,
    const float* previous_salaries,
    float* growth_rates,
    int n
) {
    unsigned int i = blockIdx.x * blockDim.x + threadIdx.x;

    if (i < n) {
        float prev = previous_salaries[i];
        float curr = current_salaries[i];

        if (prev > 0) {
            growth_rates[i] = ((curr - prev) / prev) * 100.0f;
        } else {
            growth_rates[i] = 0.0f;
        }
    }
}

/**
 * Kernel: Outlier Detection using IQR method
 * Marks salaries outside 1.5 * IQR as outliers
 */
extern "C" __global__
void salary_outlier_detection_kernel(
    const float* salaries,
    int* outliers,
    float q1,
    float q3,
    int n
) {
    unsigned int i = blockIdx.x * blockDim.x + threadIdx.x;

    if (i < n) {
        float iqr = q3 - q1;
        float lower_bound = q1 - 1.5f * iqr;
        float upper_bound = q3 + 1.5f * iqr;

        float salary = salaries[i];
        outliers[i] = (salary < lower_bound || salary > upper_bound) ? 1 : 0;
    }
}

/**
 * Kernel: Time Series Moving Average
 * Computes moving average for salary trends
 */
extern "C" __global__
void salary_moving_average_kernel(
    const float* salaries,
    float* moving_avg,
    int window_size,
    int n
) {
    unsigned int i = blockIdx.x * blockDim.x + threadIdx.x;

    if (i < n) {
        float sum = 0.0f;
        int count = 0;

        int start = max(0, (int)i - window_size / 2);
        int end = min(n - 1, (int)i + window_size / 2);

        for (int j = start; j <= end; j++) {
            sum += salaries[j];
            count++;
        }

        moving_avg[i] = sum / count;
    }
}

/**
 * Kernel: Correlation Calculation
 * Computes Pearson correlation between salary and another metric
 */
extern "C" __global__
void salary_correlation_kernel(
    const float* salaries,
    const float* other_metric,
    float* sum_xy,
    float* sum_x,
    float* sum_y,
    float* sum_x2,
    float* sum_y2,
    int n
) {
    extern __shared__ float sdata[];

    unsigned int tid = threadIdx.x;
    unsigned int i = blockIdx.x * blockDim.x + threadIdx.x;

    float x = (i < n) ? salaries[i] : 0;
    float y = (i < n) ? other_metric[i] : 0;

    sdata[tid] = x * y;
    sdata[tid + blockDim.x] = x;
    sdata[tid + 2 * blockDim.x] = y;
    sdata[tid + 3 * blockDim.x] = x * x;
    sdata[tid + 4 * blockDim.x] = y * y;
    __syncthreads();

    // Reduction
    for (unsigned int s = blockDim.x / 2; s > 0; s >>= 1) {
        if (tid < s) {
            for (int k = 0; k < 5; k++) {
                sdata[tid + k * blockDim.x] += sdata[tid + s + k * blockDim.x];
            }
        }
        __syncthreads();
    }

    if (tid == 0) {
        atomicAdd(sum_xy, sdata[0]);
        atomicAdd(sum_x, sdata[blockDim.x]);
        atomicAdd(sum_y, sdata[2 * blockDim.x]);
        atomicAdd(sum_x2, sdata[3 * blockDim.x]);
        atomicAdd(sum_y2, sdata[4 * blockDim.x]);
    }
}

/**
 * Kernel: Parallel Sort (Bitonic Sort) for Median Calculation
 * Sorts salary array for accurate median computation
 */
extern "C" __global__
void bitonic_sort_kernel(float* data, int n, int j, int k) {
    unsigned int i = blockIdx.x * blockDim.x + threadIdx.x;
    unsigned int ixj = i ^ j;

    if (ixj > i && i < n && ixj < n) {
        if ((i & k) == 0) {
            if (data[i] > data[ixj]) {
                float temp = data[i];
                data[i] = data[ixj];
                data[ixj] = temp;
            }
        } else {
            if (data[i] < data[ixj]) {
                float temp = data[i];
                data[i] = data[ixj];
                data[ixj] = temp;
            }
        }
    }
}
