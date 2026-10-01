# using dfs
class Solution {
    public:
        bool dfs(int s, int t, vector<vector<int>>& graph,vector<bool>& visited) {
            if(s == t) return true;
            visited[s] = true;
            for(int n: graph[s]) {
                if(!visited[n]) {
                    if(dfs(n,t,graph, visited)) {
                        return true;
                    }
                }
            }
            return false;
        }
        bool validPath(int n, vector<vector<int>>& edges, int source, int destination) {
            vector<bool> visited(n, false);
            vector<vector<int>> graph(n);
            for(vector<int> x: edges) {
                graph[x[0]].push_back(x[1]);
                graph[x[1]].push_back(x[0]);
            }
            return dfs(source, destination, graph, visited);
        }
    };

# using bfs
class Solution {
    public:
        bool bfs(int s, int t, vector<vector<int>>& graph,vector<bool>& visited) {
            if(s == t) return true;
            visited[s] = true;
            queue<int> q;
            q.push(s);
            while(!q.empty()) {
                int a = q.front();
                q.pop();
                for(int n: graph[a]) {
                    if(!visited[n]) {
                        if(n == t) return true;
                        visited[n] = true;
                        q.push(n);
                    }
                }
            }
            return false;
        }
        bool validPath(int n, vector<vector<int>>& edges, int source, int destination) {
            vector<bool> visited(n, false);
            vector<vector<int>> graph(n);
            for(vector<int> x: edges) {
                graph[x[0]].push_back(x[1]);
                graph[x[1]].push_back(x[0]);
            }
            return bfs(source, destination, graph, visited);
        }
    };