// start by start time
class Solution {
    public:
        int eraseOverlapIntervals(vector<vector<int>>& intervals) {
            sort(intervals.begin(), intervals.end());
            int n = intervals.size();
            int ans = 0;
            int prevEnd = intervals[0][1];
            for(int i=1;i<n;i++) {
                if(prevEnd > intervals[i][0]) {
                    ans++;
                    prevEnd = min(prevEnd, intervals[i][1]);
                } else {
                    prevEnd = intervals[i][1];
                }
            }
            return ans;
        }
    };

// sort by end time
class Solution {
    public:
        int eraseOverlapIntervals(vector<vector<int>>& intervals) {
            sort(
                intervals.begin(), intervals.end(),
                [](vector<int>& a, vector<int>& b) {
                    return a[1] < b[1];
                }
            );
            int n = intervals.size();
            int ans = 0;
            int prevEnd = INT_MIN;
            for(const auto& interval: intervals) {
                if(prevEnd > interval[0]) {
                    ans++;
                } else {
                    prevEnd = interval[1];
                }
            }
            return ans;
        }
    };