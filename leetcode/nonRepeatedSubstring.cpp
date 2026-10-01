class Solution {
    public:
        int lengthOfLongestSubstring(string s) {
            unordered_map<char, int> mp;
            int i =0;
            int ans = 0;
            for(int j=0; j<s.size();j++) {
                if(mp.count(s[j])) {
                    i = max(i, mp[s[j]] + 1);
                }

                mp[s[j]] = j;
                ans = max(ans, j-i + 1);
            }
            return ans;
        }
    };