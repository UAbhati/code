// recursive 2d dp
class Solution {
    public:
        int solve(int i, int amount, vector<int>& coins, vector<vector<int>>& dp) {
            if(amount == 0) return 1;
            if(i >= coins.size() || amount < 0) return 0;
            if(dp[i][amount] != -1) return dp[i][amount];
            return dp[i][amount] = solve(i, amount - coins[i], coins, dp) + solve(i+1, amount, coins, dp);
        }
        int change(int amount, vector<int>& coins) {
            int n = coins.size();
            vector<vector<int>> dp(n, vector<int>(amount+1, -1));
            return solve(0, amount, coins, dp);
        }
    };

// bottom up dp
class Solution {
    public:
        int change(int amount, vector<int>& coins) {
            // int g = 0;
            // for (int coin : coins) {
            //     g = gcd(g, coin);
            // }

            // if (amount % g != 0) return 0;
            vector<int> dp(amount +1, 0);
            dp[0] = 1;
            for(int coin: coins) {
                for(int a = coin; a<= amount; a++) {
                    dp[a] += dp[a-coin];
                }
            }
            return dp[amount];
        }
    };