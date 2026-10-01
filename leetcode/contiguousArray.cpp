class Solution {
    public:
        int findMaxLength(vector<int>& nums) {
            unordered_map<int, int> first;
            first[0] = -1;
            int n = nums.size();
            int ans = 0;
            int sum = 0;
            for(int i=0;i<n;i++) {
                sum += (nums[i] == 0 ? -1 : 1);
                if(first.count(sum)) {
                    ans = max(ans, i - first[sum]);
                } else {
                    first[sum] = i;
                }
            }
            return ans;
        }
    };