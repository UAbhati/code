class Solution {
    public:
        void dfs(vector<vector<char>>& grid, int i, int j, int n, int m) {
            if(i<0 || j<0 || i>=n || j>=m || grid[i][j] == '0') return;
            grid[i][j] = '0';
            dfs(grid, i+1,j,n,m);
            dfs(grid, i,j+1,n,m);
            dfs(grid, i,j-1,n,m);
            dfs(grid, i-1,j,n,m);
        }
        int numIslands(vector<vector<char>>& grid) {
            int n = grid.size();
            int m = grid[0].size();
            int ans = 0;
            for(int i=0;i<n;i++) {
                for(int j=0;j<m;j++) {
                    if(grid[i][j] == '1') {
                        ans++;
                        dfs(grid,i,j,n,m);
                    }
                }
            }
            return ans;
        }
    };

// with BFS
class Solution {
    public:
        int numIslands(vector<vector<char>>& grid) {
            int n = grid.size();
            int m = grid[0].size();
            int dx[] = {1,-1,0,0};
            int dy[] = {0,0,1,-1};
            int ans = 0;
            queue<pair<int,int>> q;
            for(int i=0;i<n;i++) {
                for(int j=0;j<m;j++) {
                    if(grid[i][j] == '1') {
                        q.push({i,j});
                        grid[i][j] = '0';
                        ans++;
                        while(!q.empty()) {
                            auto [x,y] = q.front();
                            q.pop();
                            for(int k =0;k<4;k++) {
                                int nx = x + dx[k];
                                int ny = y + dy[k];
                                if(nx >= 0 && nx < n && ny >=0 && ny <m && grid[nx][ny] == '1') {
                                    grid[nx][ny] = '0';
                                    q.push({nx,ny});
                                }
                            }
                        }
                    }
                }
            }
            return ans;
        }
    };