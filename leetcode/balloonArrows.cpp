class Solution {
    public:
        int findMinArrowShots(vector<vector<int>>& points) {
            sort(points.begin(),points.end());
            int n = points.size();
            int count = 1;
            int minEnd = points[0][1];

            for(int i=1;i<n;i++) {
                if(minEnd >= points[i][0]) {
                    minEnd = min(minEnd, points[i][1]);
                } else {
                    count++;
                    minEnd = points[i][1];
                }
            }

            return count;
        }
    };