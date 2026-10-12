class Solution {
    public:
        int maxProfit(vector<int>& prices) {
            int ans = 0;
            int minPrice = prices[0];
            int n = prices.size();
            for(int i=1;i<n;i++) {
                ans = max(ans, prices[i] - minPrice);
                minPrice = min(minPrice, prices[i]);
            }
            return ans;
        }
    };