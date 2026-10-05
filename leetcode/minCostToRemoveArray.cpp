class Solution {
    public:
        int n;
        vector<vector<long long>> dp;

        long long solve(int i, int j, vector<int>& nums) {
            int k = max(i, j) + 1;

            // Fewer than 3 elements remain.
            if (k >= n) {
                return max(nums[i], nums[j]);
            }

            // Already computed.
            if (dp[i][j] != -1) {
                return dp[i][j];
            }

            // Remove i and j, keep k.
            long long cost1 = max(nums[i], nums[j])
                            + solve(k, k + 1, nums);

            // Remove i and k, keep j.
            long long cost2 = max(nums[i], nums[k])
                            + solve(j, k + 1, nums);

            // Remove j and k, keep i.
            long long cost3 = max(nums[j], nums[k])
                            + solve(i, k + 1, nums);

            return dp[i][j] = min({cost1, cost2, cost3});
        }

        int minCost(vector<int>& nums) {
            n = nums.size();

            if (n == 1) {
                return nums[0];
            }

            if (n == 2) {
                return max(nums[0], nums[1]);
            }

            dp.assign(n, vector<long long>(n, -1));

            return solve(0, 1, nums);
        }
    };