class Solution {
    public:
        vector<vector<int>> merge(vector<vector<int>>& intervals) {
            sort(intervals.begin(), intervals.end());

            int j = 0;

            for (int i = 1; i < intervals.size(); i++) {
                if (intervals[j][1] >= intervals[i][0]) {
                    intervals[j][1] = max(intervals[j][1], intervals[i][1]);
                } else {
                    j++;
                    intervals[j] = intervals[i];
                }
            }

            intervals.resize(j + 1);
            return intervals;
        }
    };


// extra space solution
class Solution {
    public:
        vector<vector<int>> merge(vector<vector<int>>& intervals) {
            sort(intervals.begin(), intervals.end());

            vector<vector<int>> ans;
            vector<int> curr = intervals[0];

            for (int i = 1; i < intervals.size(); i++) {
                if (curr[1] >= intervals[i][0]) {
                    curr[1] = max(curr[1], intervals[i][1]);
                } else {
                    ans.push_back(curr);
                    curr = intervals[i];
                }
            }

            ans.push_back(curr);
            return ans;
        }
    };