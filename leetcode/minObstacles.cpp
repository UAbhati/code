class Solution {
    public:
        int minimumObstacles(vector<vector<int>>& grid) {
            int n = grid.size();
            int m = grid[0].size();
            vector<vector<int>> dp(n,vector<int>(m,INT_MAX));
            deque<pair<int,int>> dq;
            dq.push_front({0,0});
            dp[0][0] = 0;
            int dx[] = {1,-1,0,0};
            int dy[] = {0,0,1,-1};
            while(!dq.empty()) {
                auto [x, y] = dq.front();
                dq.pop_front();
                for(int k=0;k<4;k++) {
                    int nx = x + dx[k];
                    int ny = y + dy[k];
                    if (nx < 0 || nx >= n || ny < 0 || ny >= m)
                        continue;
                    int newCost = dp[x][y] + grid[nx][ny];
                    if (newCost < dp[nx][ny]) {
                        dp[nx][ny] = newCost;

                        if (grid[nx][ny] == 0)
                            dq.push_front({nx, ny});
                        else
                            dq.push_back({nx, ny});
                    }
                }
            }
            return dp[n-1][m-1];
        }
    };