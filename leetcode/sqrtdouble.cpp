double sqrt(double x) {
    if(x < 0) return -1;
    double l = 0;
    double r = max(1.0, x);
    double ans = 1;
    double eps = 1e-9;
    while(r-l > eps) {
        double mid = l + (r-l)/2;
        if(mid*mid < x) {
            l = mid;
        } else {
            r = mid;
        }
    }
    return (l+r)/2;
}