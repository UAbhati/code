class Solution {
    public:
        int rob(vector<int>& nums) {
            int n = nums.size();
            vector<int> dp(n+2, 0);
            for(int i=n-1;i>=0;i--) {
                dp[i] = max(dp[i+1], nums[i] + dp[i+2]);
            }
            return dp[0];
        }
    };

// recursive

class Solution {
    public:
        int solve(int i, vector<int>& nums, vector<int>& dp) {
            int n = nums.size();

            if (i >= n) return 0;

            if (dp[i] != -1) return dp[i];

            int rob = nums[i] + solve(i + 2, nums, dp);
            int skip = solve(i + 1, nums, dp);

            return dp[i] = max(rob, skip);
        }

        int rob(vector<int>& nums) {
            int n = nums.size();
            vector<int> dp(n, -1);

            return solve(0, nums, dp);
        }
    };
